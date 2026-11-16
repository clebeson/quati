"""RegistryPort use cases (M14, RFC-015): install, register_definition, bind, unbind,
transition, review and the per-load catalog with digest recheck.

Definitions, bindings and measured assurance are stored in separate sections. Only the
domain reducers change a record; every mutation is one compare-and-swap commit.
"""

from __future__ import annotations

import copy
import re
import shutil
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any, Callable, Mapping

from jsonschema.exceptions import SchemaError

from quati.behavior.contracts import ContractCatalog, default_catalog
import json

from quati.behavior.manifest import MANIFEST_FILE, load_capability_package
from quati.domain.canonical import digest
from quati.domain.capability_import import mcp_tool_manifest
from quati.domain.capability_lint import lint_package
from quati.domain.capability_registry import (
    EFFECT_ORDER, FIXTURE_LABEL, Actor, Refusal, RegistryApproval, RegistryPolicy, TransitionFacts, effect_above,
    effective_effect,
    expire_assurance, iso, measured_assurance, new_record, not_found, parse_ref, review_effect, semver_key,
    transition_record)
from quati.domain.diagnostics import ContractViolation
from quati.domain.discovery import CatalogEntry

RECORD_SCHEMA = "capability-registry-record.schema.json"
BINDING_SCHEMA = "agent-binding.schema.json"
APPROVAL_TTL_S = 900
FIXTURE_REF = re.compile(r"^fixture:([a-z][a-z0-9-]{0,63})$")
_DEFAULT = object()


def envelope(status: str = "SUCCEEDED", data: Any = None, *, code: str | None = None, message: str | None = None,
             next_action: str | None = None, uncertainties=()) -> dict:
    """The runtime-boundaries Response; the reason tag is ``error.message`` and ``data.reason``."""
    return {"status": status, "data": data, "evidence_refs": [], "uncertainties": list(uncertainties),
            "next_action": next_action,
            "error": None if code is None else {"code": code, "message": message, "retryable": False}}


def _binding_failed(message: str) -> Refusal:
    return Refusal("BLOCKED", "INVALID_INPUT", "BINDING_CHECK_FAILED", message)


def _max_effect(*effects: str) -> str:
    return max(effects, key=EFFECT_ORDER.index)


@dataclass(frozen=True)
class CatalogSnapshot:
    entries: tuple[CatalogEntry, ...]
    bindings: Mapping[str, tuple[dict, ...]] = field(default_factory=dict)
    records: Mapping[str, dict] = field(default_factory=dict)


class RegistryService:
    def __init__(self, store, handlers, *, clock: Callable, ids: Callable[[str], str],
                 catalog: ContractCatalog | None = None, policy: RegistryPolicy | None = None,
                 lint: Any = _DEFAULT) -> None:
        self.store = store
        self.handlers = handlers
        self.clock = clock
        self.ids = ids
        self.contracts = catalog or default_catalog()
        self.policy = policy or RegistryPolicy()
        self.lint = lint_package if lint is _DEFAULT else lint

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _actor(context) -> Actor:
        return Actor(context.actor_id, context.tenant_id, context.principal_kind)

    @staticmethod
    def _key(item: Mapping[str, Any]) -> tuple[str, str, str]:
        return item["tenant_id"], item["capability_id"], item["capability_version"]

    def _record(self, state: dict, tenant_id: str, ref: Any) -> dict:
        capability_id, version = parse_ref(ref)
        for record in state["records"]:
            if self._key(record) == (tenant_id, capability_id, version):
                return record
        raise not_found()

    def _definition(self, state: dict, record: Mapping[str, Any]) -> dict:
        return next(item for item in state["definitions"] if self._key(item) == self._key(record))

    def _bindings(self, state: dict, record: Mapping[str, Any]) -> list[dict]:
        return sorted((item for item in state["bindings"] if self._key(item) == self._key(record)),
                      key=lambda item: item["binding"]["id"])

    def _handler_effect(self, state: dict, record: Mapping[str, Any]) -> str | None:
        """Highest TRUSTED effect of the bound in-source handlers (never the manifest's claim)."""
        effects = []
        for item in self._bindings(state, record):
            handler = self.handlers.resolve(item["handler"])
            effects.append("dangerous" if handler is None else handler.trusted_effect)
        return _max_effect(*effects) if effects else None

    def _declared_effect(self, state: dict, record: Mapping[str, Any]) -> str:
        """Bound: the trusted handler floor (a review may only raise it). Unbound: the manifest
        claim, used only for the VALIDATED effect-ceiling check."""
        handler_effect = self._handler_effect(state, record)
        if handler_effect is None:
            return record["effect_class_reviewed"] or self._definition(state, record)["manifest"]["effects"]
        return _max_effect(handler_effect, record["effect_class_reviewed"] or handler_effect)

    def _verified_manifest(self, record: Mapping[str, Any]) -> dict | None:
        """The manifest parsed from the stored package bytes, only when their digest matches the record."""
        package = self.store.read_package(record["capability_id"], record["capability_version"])
        if package is None or package[0] != record["package_sha256"]:
            return None
        return json.loads(package[1][MANIFEST_FILE])     # same digest => the bytes validated at install

    def _facts(self, state: dict, record: Mapping[str, Any], approval: RegistryApproval | None = None
               ) -> TransitionFacts:
        bindings = self._bindings(state, record)
        best = max(bindings, key=lambda item: item["measured_assurance"], default=None)
        stored = next((item for item in state["approvals"]
                       if approval is not None and item["approval"]["approval_id"] == approval.approval_id), None)
        return TransitionFacts(
            now=self.clock(), declared_effect=self._declared_effect(state, record),
            binding_ids=tuple(item["binding"]["id"] for item in bindings),
            measured=best["measured_assurance"] if best else "C0",
            self_test_evidence=best["self_test_evidence_sha256"] if best else None,
            fixture_only=bool(bindings) and all(FIXTURE_REF.fullmatch(item["binding"]["implementation_ref"])
                                                for item in bindings),
            secret_slots=len(self._definition(state, record)["manifest"].get("secret_slots", [])),
            approval=approval, approval_known=stored is not None and stored["approval"] == approval.to_json(),
            approval_consumed=stored is not None and stored["consumed_at"] is not None)

    def _replace(self, state: dict, old: dict, new: dict, actor_id: str, pending: list,
                 approval_id: str | None = None) -> dict:
        state["records"][state["records"].index(old)] = new
        if new["lifecycle"] != old["lifecycle"]:
            state["history"].append({"tenant_id": new["tenant_id"], "capability_id": new["capability_id"],
                                     "capability_version": new["capability_version"], "from": old["lifecycle"],
                                     "to": new["lifecycle"], "revision": new["revision"],
                                     "previous_revision": old["revision"], "actor_id": actor_id,
                                     "approval_id": approval_id, "at": new["updated_at"]})
            pending.append({"event": "registry.transition", "capability_id": new["capability_id"],
                            "capability_version": new["capability_version"], "from": old["lifecycle"],
                            "to": new["lifecycle"], "revision": new["revision"], "actor_id": actor_id,
                            "approval_id": approval_id})
        return new

    def _audit(self, event: dict) -> None:
        self.store.append_audit({"at": iso(self.clock()), **event})

    def _commit(self, state: dict, revision: int, pending: list, *, operation: str = "update",
                ref: Any = None) -> None:
        """Write-ahead audit (audit P3): the intent is durable before the CAS commit, the outcome after."""
        for record in state["records"]:
            if self.contracts.errors(record, RECORD_SCHEMA):
                raise Refusal("BLOCKED", "INTERNAL_ERROR", "RECORD_SCHEMA_INVALID", "registry record is invalid")
        intent = {"operation": operation, "ref": None if ref is None else str(ref), "expected_revision": revision}
        self._audit({"event": "registry.intent", **intent, "events_sha256": digest({"events": pending})})
        try:
            self.store.commit(state, expected_revision=revision)
        except Exception as exc:
            self._audit({"event": "registry.outcome", **intent, "status": "FAILED",
                         "reason": getattr(exc, "reason", type(exc).__name__)})
            raise
        for event in pending:
            self._audit(event)
        self._audit({"event": "registry.outcome", **intent, "status": "COMMITTED", "revision": revision + 1})

    def _transition(self, state: dict, context, ref: Any, target: str, pending: list, *, approval=None,
                    expected_revision: Any = None) -> dict:
        record = self._record(state, context.tenant_id, ref)
        facts = self._facts(state, record, approval)
        new = transition_record(record, target, expected_revision=record["revision"] if expected_revision is None
                                else expected_revision, actor=self._actor(context), facts=facts, policy=self.policy)
        approval_id = None
        if target == "ENABLED":
            approval_id = approval.approval_id
            stored = next(item for item in state["approvals"] if item["approval"]["approval_id"] == approval_id)
            stored["consumed_at"] = iso(facts.now)
            pending.append({"event": "registry.activation", "capability_id": new["capability_id"],
                            "capability_version": new["capability_version"], "approval": approval.to_json(),
                            "approval_evidence_sha256": approval.evidence_sha256, "label": FIXTURE_LABEL,
                            "actor_id": context.actor_id})
        return self._replace(state, record, new, context.actor_id, pending, approval_id)

    def _mint(self, state: dict, context, record: Mapping[str, Any], kind: str, effect: str) -> RegistryApproval:
        now = self.clock()
        approval = RegistryApproval(
            approval_id=self.ids("approval"), kind=kind, approver_id=context.actor_id,
            approver_kind=context.principal_kind, tenant_id=context.tenant_id,
            capability_id=record["capability_id"], capability_version=record["capability_version"],
            binding_ids=tuple(item["binding"]["id"] for item in self._bindings(state, record))
            if kind == "FIXTURE_ENABLE" else (),
            effect_class=effect, issued_at=iso(now), expires_at=iso(now + timedelta(seconds=APPROVAL_TTL_S)))
        state["approvals"].append({"approval": approval.to_json(), "consumed_at": None})
        return approval

    def _bind(self, state: dict, context, ref: Any, binding: Any, pending: list,
              manifest: Mapping[str, Any] | None = None) -> None:
        if context.principal_kind != "HUMAN":
            raise Refusal("DENIED", "FORBIDDEN", "OPERATOR_REQUIRED", "only a HUMAN operator binds past VALIDATED")
        record = self._record(state, context.tenant_id, ref)
        if record["lifecycle"] in ("DRAFT", "DISABLED", "DEPRECATED"):
            raise _binding_failed(f"a {record['lifecycle']} capability cannot be bound")
        if not isinstance(binding, Mapping) or self.contracts.errors(dict(binding), BINDING_SCHEMA):
            raise _binding_failed("the binding does not match agent-binding.schema.json")
        if (binding["capability_id"], binding["capability_version"]) != (record["capability_id"],
                                                                         record["capability_version"]):
            raise _binding_failed("the binding names another capability")
        match = FIXTURE_REF.fullmatch(binding["implementation_ref"])
        if binding["adapter_type"] != "mock" or match is None or self.handlers.resolve(match.group(1)) is None:
            raise _binding_failed("S00 binds only registered in-source fixture handlers")
        if any(item["binding"]["id"] == binding["id"] for item in self._bindings(state, record)):
            raise _binding_failed("the binding id is already bound")
        manifest = self._verified_manifest(record) if manifest is None else manifest
        if manifest is None:
            raise Refusal("DENIED", "FORBIDDEN", "DIGEST_MISMATCH", "the stored package does not match its digest")
        handler = self.handlers.resolve(match.group(1))
        if (manifest["id"] != handler.trusted_capability_id
                or effect_above(handler.trusted_effect, manifest["effects"])
                or not set(handler.trusted_permissions) <= set(manifest["permissions"])):
            raise Refusal("DENIED", "FORBIDDEN", "HANDLER_IDENTITY_MISMATCH",
                          "the handler's trusted capability id, effect or permission floor does not match")
        evidence = self.handlers.self_test(match.group(1), manifest, now=self.clock())
        if evidence is None:
            raise _binding_failed("the fixture self-test does not satisfy the capability contract")
        stored = {"binding_ref": f"{record['capability_id']}@{record['capability_version']}#{binding['id']}",
                  "tenant_id": record["tenant_id"], "capability_id": record["capability_id"],
                  "capability_version": record["capability_version"], "binding": dict(binding),
                  "binding_sha256": digest(dict(binding)), "handler": match.group(1),
                  "handler_effect": handler.trusted_effect,
                  "measured_assurance": measured_assurance(binding["verification"], True),
                  "self_test_evidence_sha256": evidence, "healthy": True}
        state["bindings"].append(stored)
        pending.append({"event": "registry.bind", "binding_ref": stored["binding_ref"],
                        "measured_assurance": stored["measured_assurance"], "self_test_evidence_sha256": evidence,
                        "actor_id": context.actor_id})
        if record["lifecycle"] in ("STAGED", "ENABLED"):
            self._replace(state, record, expire_assurance(record, now=self.clock()), context.actor_id, pending)

    def _binding_entry(self, state: dict, context, binding_ref: Any) -> dict:
        for item in state["bindings"]:
            if item["binding_ref"] == binding_ref and item["tenant_id"] == context.tenant_id:
                return item
        raise Refusal("DENIED", "NOT_FOUND", "BINDING_NOT_FOUND", "no such binding")

    @staticmethod
    def _require_operator(context) -> None:
        if context.principal_kind not in ("HUMAN", "SERVICE"):
            raise Refusal("DENIED", "FORBIDDEN", "OPERATOR_REQUIRED", "only an operator changes bindings")

    def _summary(self, state: dict, record: Mapping[str, Any]) -> dict:
        fixture = any(FIXTURE_REF.fullmatch(item["binding"]["implementation_ref"])
                      for item in self._bindings(state, record))
        return {"definition_ref": f"{record['capability_id']}@{record['capability_version']}",
                "lifecycle": record["lifecycle"], "assurance": record["assurance"],
                "package_sha256": record["package_sha256"], "label": FIXTURE_LABEL if fixture else None}

    # ------------------------------------------------------------------ RegistryPort
    def install(self, context, path: Path, *, source: str, fixture_handler: str | None = None,
                enable_fixture: bool = False, import_kind: str = "scs",
                vendor_hints: Mapping[str, Any] | None = None) -> dict:
        """Validate and copy a package, then DRAFT -> VALIDATED; a fixture handler stages it and the
        explicit ``enable_fixture`` operator flag mints a single-use FIXTURE_ENABLE approval."""
        try:
            package = load_capability_package(Path(path), catalog=self.contracts)
        except ContractViolation as exc:
            return envelope("BLOCKED", {"reason": exc.reason}, code=exc.code.value, message=exc.reason)
        except (ValueError, OSError, SchemaError):
            return envelope("BLOCKED", {"reason": "SCHEMA_UNAVAILABLE"}, code="CONFIG_INVALID",
                            message="SCHEMA_UNAVAILABLE")
        with self.store.transaction():          # audit P1-4: one lock from load to publish
            return self._install_locked(context, package, source=source, fixture_handler=fixture_handler,
                                        enable_fixture=enable_fixture, import_kind=import_kind,
                                        vendor_hints=vendor_hints)

    def _install_locked(self, context, package, *, source: str, fixture_handler: str | None, enable_fixture: bool,
                        import_kind: str, vendor_hints: Mapping[str, Any] | None) -> dict:
        manifest, now = package.manifest, self.clock()
        ref = f"{manifest['id']}@{manifest['version']}"
        state = self.store.load()
        revision = state["revision"]
        try:
            existing = self._record(state, context.tenant_id, ref)
        except Refusal:
            existing = None
        if existing is not None:
            if existing["package_sha256"] == package.package_sha256:
                if self.store.package_digest(manifest["id"], manifest["version"]) != package.package_sha256:
                    _sha, staging = self.store.stage_package(package.entries)     # repair an interrupted publish
                    self.store.publish_package(manifest["id"], manifest["version"], staging)
                return envelope("SUCCEEDED", {**self._summary(state, existing), "already_installed": True})
            self._audit({"event": "registry.install_refused", "capability_id": manifest["id"],
                         "capability_version": manifest["version"], "reason": "VERSION_EXISTS",
                         "actor_id": context.actor_id})
            return envelope("CONFLICT", {**self._summary(state, existing), "reason": "VERSION_EXISTS"},
                            code="REVISION_CONFLICT", message="VERSION_EXISTS")
        _sha, staging = self.store.stage_package(package.entries)       # content-addressed, not yet visible
        try:
            return self._install_staged(context, package, staging, state, revision, ref, now, source=source,
                                        fixture_handler=fixture_handler, enable_fixture=enable_fixture,
                                        import_kind=import_kind, vendor_hints=vendor_hints)
        finally:
            self.store.discard_staging(staging)

    def _install_staged(self, context, package, staging: Path, state: dict, revision: int, ref: str, now, *,
                        source: str, fixture_handler: str | None, enable_fixture: bool, import_kind: str,
                        vendor_hints: Mapping[str, Any] | None) -> dict:
        manifest = package.manifest
        files = {entry.path: entry.data for entry in package.entries if entry.path != MANIFEST_FILE}
        report = self.lint(manifest, files) if self.lint is not None else None
        record = new_record(tenant_id=context.tenant_id, capability_id=manifest["id"],
                            capability_version=manifest["version"], package_sha256=package.package_sha256,
                            source=source, import_kind=import_kind, now=now, vendor_hints=vendor_hints)
        record["lint_report_ref"] = None if report is None else f"sha256:{digest(report)}"
        state["definitions"].append({"tenant_id": context.tenant_id, "capability_id": manifest["id"],
                                     "capability_version": manifest["version"],
                                     "package_sha256": package.package_sha256, "manifest": manifest,
                                     "lint_report": report})
        state["records"].append(record)
        state["history"].append({"tenant_id": context.tenant_id, "capability_id": manifest["id"],
                                 "capability_version": manifest["version"], "from": None, "to": "DRAFT",
                                 "revision": 0, "previous_revision": None, "actor_id": context.actor_id,
                                 "approval_id": None, "at": iso(now)})
        pending: list = [{"event": "registry.installed", "capability_id": manifest["id"],
                          "capability_version": manifest["version"], "package_sha256": package.package_sha256,
                          "source": source, "actor_id": context.actor_id}]
        refusal = None
        try:
            self._transition(state, context, ref, "VALIDATED", pending)
            if fixture_handler is not None:
                binding = self.fixture_binding(ref, fixture_handler)
                self._bind(state, context, ref, binding, pending, manifest=manifest)
                self._transition(state, context, ref, "STAGED", pending)
                if enable_fixture:              # _bind already refused every non-HUMAN principal (audit P3)
                    current = self._record(state, context.tenant_id, ref)
                    approval = self._mint(state, context, current, "FIXTURE_ENABLE",
                                          self._declared_effect(state, current))
                    self._transition(state, context, ref, "ENABLED", pending, approval=approval)
        except Refusal as exc:
            refusal = exc
            pending.append({"event": "registry.transition_refused", "capability_id": manifest["id"],
                            "capability_version": manifest["version"], "reason": exc.reason,
                            "actor_id": context.actor_id})
        try:
            self._commit(state, revision, pending, operation="install", ref=ref)
        except Refusal as exc:
            if exc.reason != "REVISION_CONFLICT":
                raise
            return envelope("CONFLICT", {"definition_ref": ref, "reason": "REVISION_CONFLICT"},
                            code="REVISION_CONFLICT", message="REVISION_CONFLICT")
        self.store.publish_package(manifest["id"], manifest["version"], staging)   # only after the CAS won
        self.store.write_lock_entry({"id": manifest["id"], "version": manifest["version"],
                                     "sha256": package.package_sha256, "source": source,
                                     "installed_by_approval": None, "installed_at": iso(now)})
        summary = self._summary(state, self._record(state, context.tenant_id, ref))
        if refusal is not None:
            return envelope(refusal.status, {**summary, "reason": refusal.reason}, code=refusal.code,
                            message=refusal.reason)
        return envelope("SUCCEEDED", summary)

    def register_definition(self, context, path: Path, *, source: str) -> dict:
        return self.install(context, path, source=source)

    def import_mcp_tool(self, context, tool: Mapping[str, Any], *, server: str, server_version: str,
                        intents: Mapping[str, Any], quarantine: Path) -> dict:
        try:
            manifest, hints, raw = mcp_tool_manifest(tool, server=server, server_version=server_version,
                                                     intents=intents)
        except Refusal as exc:
            return envelope(exc.status, {"reason": exc.reason}, code=exc.code, message=exc.reason)
        package = Path(quarantine) / manifest["id"]
        shutil.rmtree(package, ignore_errors=True)
        package.mkdir(parents=True)
        (package / MANIFEST_FILE).write_bytes(digest_free_json(manifest))
        (package / "mcp-tool.json").write_bytes(raw)
        return self.install(context, package, source=f"mcp:{server}@{server_version}/{manifest['name']}",
                            import_kind="mcp_tool", vendor_hints=hints)

    @staticmethod
    def fixture_binding(ref: Any, handler: str, *, suffix: str = "b1") -> dict:
        capability_id, version = parse_ref(ref)
        return {"schema_version": "scs-binding/1.0", "id": f"{capability_id}.{suffix}",
                "capability_id": capability_id, "capability_version": version, "adapter_type": "mock",
                "implementation_ref": f"fixture:{handler}", "enabled": True, "requirements": [],
                "verification": "LOCAL"}

    def bind(self, context, ref: Any, binding: Mapping[str, Any]) -> None:
        self._require_operator(context)
        state, pending = self.store.load(), []
        revision = state["revision"]
        try:
            self._bind(state, context, ref, binding, pending)
        except Refusal as exc:
            self._audit({"event": "registry.bind_refused", "ref": str(ref), "reason": exc.reason,
                         "actor_id": context.actor_id})
            raise
        self._commit(state, revision, pending)

    def unbind(self, context, binding_ref: str) -> None:
        self._require_operator(context)
        state, pending = self.store.load(), []
        revision = state["revision"]
        entry = self._binding_entry(state, context, binding_ref)
        state["bindings"].remove(entry)
        record = self._record(state, context.tenant_id, f"{entry['capability_id']}@{entry['capability_version']}")
        pending.append({"event": "registry.unbind", "binding_ref": binding_ref, "actor_id": context.actor_id})
        if record["lifecycle"] in ("STAGED", "ENABLED"):
            self._replace(state, record, expire_assurance(record, now=self.clock()), context.actor_id, pending)
        self._commit(state, revision, pending)

    def set_binding_health(self, context, binding_ref: str, *, healthy: bool) -> None:
        self._require_operator(context)
        state = self.store.load()
        revision = state["revision"]
        self._binding_entry(state, context, binding_ref)["healthy"] = bool(healthy)
        self._commit(state, revision, [{"event": "registry.binding_health", "binding_ref": binding_ref,
                                        "healthy": bool(healthy), "actor_id": context.actor_id}])

    def binding_refs(self, context, ref: Any) -> list[str]:
        state = self.store.load()
        return [item["binding_ref"] for item in self._bindings(state, self._record(state, context.tenant_id, ref))]

    def transition(self, context, ref: Any, expected_revision: Any, target: str, *,
                   approval: RegistryApproval | None = None) -> dict:
        state, pending = self.store.load(), []
        revision = state["revision"]
        try:
            record = self._transition(state, context, ref, target, pending, approval=approval,
                                      expected_revision=expected_revision)
        except Refusal as exc:
            self._audit({"event": "registry.transition_refused", "ref": str(ref), "to": target,
                         "reason": exc.reason, "actor_id": context.actor_id,
                         "principal_kind": context.principal_kind})
            raise
        self._commit(state, revision, pending)
        return copy.deepcopy(record)

    def fixture_enable_approval(self, context, ref: Any) -> RegistryApproval:
        """The explicit local operator activation (``--enable-fixture``): HUMAN only, single use."""
        if context.principal_kind != "HUMAN":
            self._audit({"event": "registry.approval_refused", "ref": str(ref), "actor_id": context.actor_id,
                         "reason": "ENABLE_REQUIRES_HUMAN_APPROVAL"})
            raise Refusal("DENIED", "FORBIDDEN", "ENABLE_REQUIRES_HUMAN_APPROVAL", "only a HUMAN operator approves")
        state = self.store.load()
        revision = state["revision"]
        record = self._record(state, context.tenant_id, ref)
        approval = self._mint(state, context, record, "FIXTURE_ENABLE", self._declared_effect(state, record))
        self._commit(state, revision, [])
        return approval

    def review_approval(self, context, ref: Any, effect: str) -> RegistryApproval:
        if context.principal_kind != "HUMAN":
            raise Refusal("DENIED", "FORBIDDEN", "REVIEW_REQUIRES_HUMAN_APPROVAL", "only a HUMAN operator reviews")
        state = self.store.load()
        revision = state["revision"]
        approval = self._mint(state, context, self._record(state, context.tenant_id, ref), "CAPABILITY_REVIEW",
                              effect)
        self._commit(state, revision, [])
        return approval

    def review_effect_class(self, context, ref: Any, expected_revision: Any, effect: str, *,
                            approval: RegistryApproval | None) -> dict:
        state = self.store.load()
        revision = state["revision"]
        record = self._record(state, context.tenant_id, ref)
        new = review_effect(record, effect, expected_revision=expected_revision, actor=self._actor(context),
                            facts=self._facts(state, record, approval))
        next(item for item in state["approvals"]
             if item["approval"]["approval_id"] == approval.approval_id)["consumed_at"] = iso(self.clock())
        self._replace(state, record, new, context.actor_id, [])
        self._commit(state, revision, [{"event": "registry.effect_reviewed", "ref": str(ref), "effect": effect,
                                        "approval_id": approval.approval_id, "actor_id": context.actor_id}])
        return copy.deepcopy(new)

    # ------------------------------------------------------------------ queries
    def record(self, context, ref: Any) -> dict:
        return copy.deepcopy(self._record(self.store.load(), context.tenant_id, ref))

    def records(self, context, *, enabled_only: bool = False) -> list[dict]:
        found = [copy.deepcopy(record) for record in self.store.load()["records"]
                 if record["tenant_id"] == context.tenant_id and (not enabled_only or record["lifecycle"] == "ENABLED")]
        return sorted(found, key=lambda item: (item["capability_id"], semver_key(item["capability_version"])))

    def manifest(self, context, ref: Any) -> dict:
        state = self.store.load()
        return copy.deepcopy(self._definition(state, self._record(state, context.tenant_id, ref))["manifest"])

    def effective_effect(self, context, ref: Any) -> str:
        return effective_effect(self.record(context, ref))

    def lint_report(self, context, ref: Any) -> dict | None:
        state = self.store.load()
        return copy.deepcopy(self._definition(state, self._record(state, context.tenant_id, ref))["lint_report"])

    def catalog(self, context) -> CatalogSnapshot:
        """Load-time view: every stored package digest is recomputed; a mismatch is not loadable."""
        state = self.store.load()
        entries, bindings, records = [], {}, {}
        for record in state["records"]:
            if record["tenant_id"] != context.tenant_id:
                continue
            stored_copy = self._definition(state, record)["manifest"]
            verified = self._verified_manifest(record)
            observed = self.store.package_digest(record["capability_id"], record["capability_version"])
            loadable = verified is not None and verified == stored_copy
            manifest = verified if verified is not None else stored_copy
            if verified is not None and verified != stored_copy:
                self._audit({"event": "registry.definition_mismatch", "capability_id": record["capability_id"],
                             "capability_version": record["capability_version"], "reason": "DIGEST_MISMATCH",
                             "package_sha256": record["package_sha256"]})
            elif not loadable:
                self._audit({"event": "registry.digest_mismatch", "capability_id": record["capability_id"],
                             "capability_version": record["capability_version"], "reason": "DIGEST_MISMATCH",
                             "expected_sha256": record["package_sha256"], "observed_sha256": observed})
            bound = tuple(copy.deepcopy(item) for item in self._bindings(state, record))
            key = f"{record['capability_id']}@{record['capability_version']}"
            bindings[key], records[key] = bound, copy.deepcopy(record)
            entries.append(CatalogEntry(
                capability_id=record["capability_id"], capability_version=record["capability_version"],
                lifecycle=record["lifecycle"], loadable=loadable,
                enforced_effect=_max_effect(effective_effect(record), self._handler_effect(state, record) or "none"),
                permissions=tuple(manifest["permissions"]),
                data_class_ceiling=manifest.get("data_class_ceiling", "PUBLIC"),
                requires_models=tuple(manifest.get("compatibility", {}).get("requires_models", ())),
                bindings_healthy=any(item["healthy"] for item in bound), manifest=copy.deepcopy(manifest)))
        entries.sort(key=lambda entry: (entry.capability_id, semver_key(entry.capability_version)))
        return CatalogSnapshot(tuple(entries), bindings, records)


def digest_free_json(document: Mapping[str, Any]) -> bytes:
    import json
    return json.dumps(dict(document), sort_keys=True, indent=2).encode("utf-8") + b"\n"


__all__ = ["CatalogSnapshot", "RegistryService", "envelope"]
