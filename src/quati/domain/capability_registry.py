"""Capability registry lifecycle and assurance (RFC-015, M14) as pure functions.

Definitions (author manifests), implementation bindings and measured assurance are
separate inputs. Only the reducers here change a registry record; manifests and binding
claims are proposals, never authority. Every refusal raises ``Refusal`` with a reason.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from quati.domain.canonical import digest

RECORD_SCHEMA_VERSION = "scs-registry/1.0"
LIFECYCLES = ("DRAFT", "VALIDATED", "STAGED", "ENABLED", "DEPRECATED", "DISABLED")
ASSURANCE_LEVELS = ("C0", "C1", "C2", "C3", "C4", "C5")
VERIFICATION_ASSURANCE = {"UNVERIFIED": "C0", "CONTRACT": "C1", "LOCAL": "C2", "LLM_REAL": "C3",
                          "EXTERNAL": "C4", "PRODUCTION": "C5"}
EFFECT_ORDER = ("none", "read", "write", "dangerous")
APPROVAL_KINDS = ("FIXTURE_ENABLE", "CAPABILITY_REVIEW")
CAPABILITY_ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]*(\.[a-z][a-z0-9_-]*)+$")
VERSION_PATTERN = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
FIXTURE_LABEL = "LOCAL_FIXTURE_ONLY"
# Edges besides "any -> DISABLED"; assurance expiry is ``expire_assurance``, not an edge.
EDGES = {("DRAFT", "VALIDATED"), ("VALIDATED", "STAGED"), ("STAGED", "ENABLED"), ("ENABLED", "DEPRECATED")}


class Refusal(Exception):
    """A typed registry or discovery refusal: response status, error code and reason tag."""

    def __init__(self, status: str, code: str, reason: str, message: str = "") -> None:
        super().__init__(f"{status} {code} {reason}: {message or reason}")
        self.status = status
        self.code = code
        self.reason = reason
        self.message = message or reason


def not_found() -> Refusal:
    return Refusal("DENIED", "NOT_FOUND", "NOT_A_CAPABILITY_ID", "no registered capability has this id")


def iso(instant: datetime) -> str:
    return instant.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def semver_key(version: str) -> tuple[int, int, int]:
    major, minor, patch = (int(part) for part in version.split("."))
    return major, minor, patch


def parse_ref(ref: Any) -> tuple[str, str]:
    """``"<id>@<version>"`` or ``{"id": ..., "version": ...}``; anything else is not an id."""
    if isinstance(ref, Mapping):
        capability_id, version = ref.get("id"), ref.get("version")
    elif isinstance(ref, str) and ref.count("@") == 1:
        capability_id, version = ref.split("@")
    else:
        raise not_found()
    if not (isinstance(capability_id, str) and CAPABILITY_ID_PATTERN.fullmatch(capability_id)
            and isinstance(version, str) and VERSION_PATTERN.fullmatch(version)):
        raise not_found()
    return capability_id, version


def effect_above(effect: str, ceiling: str) -> bool:
    return EFFECT_ORDER.index(effect) > EFFECT_ORDER.index(ceiling)


def assurance_at_least(level: str, minimum: str) -> bool:
    return ASSURANCE_LEVELS.index(level) >= ASSURANCE_LEVELS.index(minimum)


def measured_assurance(claimed_verification: str, self_test_passed: bool) -> str:
    """A binding claim is capped by what a local deterministic self-test measured (C2)."""
    if not self_test_passed:
        return "C0"
    claimed = VERIFICATION_ASSURANCE[claimed_verification]
    return min(claimed, "C2", key=ASSURANCE_LEVELS.index)


def effective_effect(record: Mapping[str, Any]) -> str:
    """Enforcement uses ``dangerous`` until a human reviewed the effect class."""
    return record["effect_class_reviewed"] or "dangerous"


@dataclass(frozen=True)
class RegistryPolicy:
    max_effect_class: str = "read"
    min_enable_assurance: str = "C2"

    def __post_init__(self) -> None:
        if self.max_effect_class not in EFFECT_ORDER:
            raise ValueError("unknown effect class")
        if self.min_enable_assurance not in ASSURANCE_LEVELS or not assurance_at_least(self.min_enable_assurance,
                                                                                       "C2"):
            raise ValueError("the enable assurance floor is C2 and is never lowered")


@dataclass(frozen=True)
class Actor:
    """Built by trusted code from the authenticated RequestContext."""

    actor_id: str
    tenant_id: str
    principal_kind: str


@dataclass(frozen=True)
class RegistryApproval:
    """A single-use local HUMAN approval minted by the registry (S00: FIXTURE_ENABLE, CAPABILITY_REVIEW)."""

    approval_id: str
    kind: str
    approver_id: str
    approver_kind: str
    tenant_id: str
    capability_id: str
    capability_version: str
    binding_ids: tuple[str, ...]
    effect_class: str
    issued_at: str
    expires_at: str

    def to_json(self) -> dict:
        return {"approval_id": self.approval_id, "kind": self.kind, "approver_id": self.approver_id,
                "approver_kind": self.approver_kind, "tenant_id": self.tenant_id,
                "capability_id": self.capability_id, "capability_version": self.capability_version,
                "binding_ids": list(self.binding_ids), "effect_class": self.effect_class,
                "issued_at": self.issued_at, "expires_at": self.expires_at}

    @property
    def evidence_sha256(self) -> str:
        return digest(self.to_json())


@dataclass(frozen=True)
class TransitionFacts:
    """Trusted facts about one record, gathered by the application layer."""

    now: datetime
    declared_effect: str
    binding_ids: tuple[str, ...] = ()
    measured: str = "C0"
    self_test_evidence: str | None = None
    fixture_only: bool = False
    secret_slots: int = 0
    approval: RegistryApproval | None = None
    approval_known: bool = False
    approval_consumed: bool = False


def new_record(*, tenant_id: str, capability_id: str, capability_version: str, package_sha256: str, source: str,
               import_kind: str, now: datetime, vendor_hints: Mapping[str, Any] | None = None) -> dict:
    record = {"schema_version": RECORD_SCHEMA_VERSION, "tenant_id": tenant_id, "capability_id": capability_id,
              "capability_version": capability_version, "package_sha256": package_sha256, "source": source,
              "import_kind": import_kind, "lifecycle": "DRAFT", "assurance": "C0", "effect_class_reviewed": None,
              "assurance_evidence": [], "enabled_by_approval": None, "lint_report_ref": None,
              "updated_at": iso(now), "revision": 0}
    if vendor_hints is not None:
        record["vendor_hints"] = dict(vendor_hints)
    return record


def _evidence(level: str, evidence_sha256: str, now: datetime) -> dict:
    return {"level": level, "evidence_sha256": evidence_sha256, "model_digest": None, "catalog_digest": None,
            "recorded_at": iso(now)}


def _approval_ok(approval: RegistryApproval | None, *, kind: str, actor: Actor, record: Mapping[str, Any],
                 facts: TransitionFacts, effect: str) -> bool:
    return (approval is not None and facts.approval_known and not facts.approval_consumed
            and approval.kind == kind and approval.approver_kind == "HUMAN"
            and approval.approver_id == actor.actor_id and approval.tenant_id == record["tenant_id"]
            and approval.capability_id == record["capability_id"]
            and approval.capability_version == record["capability_version"]
            and approval.effect_class == effect and facts.now.astimezone(timezone.utc) < _instant(approval.expires_at))


def _instant(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _check_cas(record: Mapping[str, Any], expected_revision: Any) -> None:
    if type(expected_revision) is not int or expected_revision != record["revision"]:
        raise Refusal("CONFLICT", "REVISION_CONFLICT", "REVISION_CONFLICT", "stale registry record revision")


def transition_record(record: Mapping[str, Any], target: str, *, expected_revision: Any, actor: Actor,
                      facts: TransitionFacts, policy: RegistryPolicy) -> dict:
    """RFC-015 lifecycle reducer: CAS first, then the edge, then the guards of the edge."""
    _check_cas(record, expected_revision)
    if actor.tenant_id != record["tenant_id"]:
        raise not_found()
    source = record["lifecycle"]
    if target not in LIFECYCLES or (target != "DISABLED" and (source, target) not in EDGES) or source == target:
        raise Refusal("BLOCKED", "INVALID_INPUT", "TRANSITION_NOT_ALLOWED", f"{source} -> {target} is not allowed")
    changes: dict[str, Any] = {"lifecycle": target}
    if target in ("DISABLED", "DEPRECATED"):
        if actor.principal_kind not in ("HUMAN", "SERVICE"):
            raise Refusal("DENIED", "FORBIDDEN", "OPERATOR_REQUIRED", "only an operator changes lifecycle")
    elif target == "VALIDATED":
        if effect_above(facts.declared_effect, policy.max_effect_class):
            raise Refusal("DENIED", "FORBIDDEN", "EFFECT_ABOVE_CEILING", "declared effect exceeds the registry ceiling")
        changes.update(assurance="C1", assurance_evidence=[_evidence("C1", record["package_sha256"], facts.now)])
    elif target == "STAGED":
        if actor.principal_kind != "HUMAN":                                   # audit P3: past VALIDATED
            raise Refusal("DENIED", "FORBIDDEN", "OPERATOR_REQUIRED", "only a HUMAN operator stages a capability")
        if not facts.binding_ids or facts.self_test_evidence is None:
            raise Refusal("BLOCKED", "INVALID_INPUT", "BINDING_CHECK_FAILED", "no binding passed its self-test")
        if not assurance_at_least(facts.measured, "C2"):
            raise Refusal("BLOCKED", "INVALID_INPUT", "ASSURANCE_BELOW_C2", "measured assurance is below C2")
        changes.update(assurance=facts.measured,
                       assurance_evidence=[_evidence(facts.measured, facts.self_test_evidence, facts.now)])
    else:  # ENABLED
        approval = facts.approval
        if actor.principal_kind != "HUMAN" or not _approval_ok(approval, kind="FIXTURE_ENABLE", actor=actor,
                                                                record=record, facts=facts,
                                                                effect=facts.declared_effect):
            raise Refusal("DENIED", "FORBIDDEN", "ENABLE_REQUIRES_HUMAN_APPROVAL",
                          "enabling needs a fresh single-use HUMAN approval bound to this capability")
        if tuple(sorted(approval.binding_ids)) != tuple(sorted(facts.binding_ids)):
            raise Refusal("DENIED", "FORBIDDEN", "ENABLE_REQUIRES_HUMAN_APPROVAL", "approval binds other bindings")
        if not assurance_at_least(record["assurance"], policy.min_enable_assurance):
            raise Refusal("BLOCKED", "INVALID_INPUT", "ASSURANCE_BELOW_C2", "assurance is below the enable floor")
        if effect_above(facts.declared_effect, policy.max_effect_class):
            raise Refusal("DENIED", "FORBIDDEN", "EFFECT_ABOVE_CEILING", "declared effect exceeds the registry ceiling")
        if not facts.fixture_only:
            raise Refusal("BLOCKED", "UNSUPPORTED", "FIXTURE_BINDING_REQUIRED", "S00 enables fixture bindings only")
        if facts.secret_slots:
            raise Refusal("BLOCKED", "NOT_CONFIGURED", "SECRET_SLOTS_UNRESOLVED", "secret slots are not resolved")
        changes.update(enabled_by_approval=approval.approval_id, effect_class_reviewed=facts.declared_effect)
    return {**record, **changes, "updated_at": iso(facts.now), "revision": record["revision"] + 1}


def expire_assurance(record: Mapping[str, Any], *, now: datetime) -> dict:
    """A binding, digest or measured-model change resets assurance to C0 and lifecycle to <= VALIDATED."""
    lifecycle = "VALIDATED" if record["lifecycle"] in ("STAGED", "ENABLED") else record["lifecycle"]
    return {**record, "lifecycle": lifecycle, "assurance": "C0", "assurance_evidence": [],
            "enabled_by_approval": None, "updated_at": iso(now), "revision": record["revision"] + 1}


def review_effect(record: Mapping[str, Any], effect: str, *, expected_revision: Any, actor: Actor,
                  facts: TransitionFacts) -> dict:
    """A HUMAN-approved review of the enforced effect class; vendor hints never take part."""
    if effect not in EFFECT_ORDER or actor.principal_kind != "HUMAN" or not _approval_ok(
            facts.approval, kind="CAPABILITY_REVIEW", actor=actor, record=record, facts=facts, effect=effect):
        raise Refusal("DENIED", "FORBIDDEN", "REVIEW_REQUIRES_HUMAN_APPROVAL",
                      "an effect class review needs a fresh single-use HUMAN approval")
    _check_cas(record, expected_revision)
    return {**record, "effect_class_reviewed": effect, "updated_at": iso(facts.now),
            "revision": record["revision"] + 1}


__all__ = ["APPROVAL_KINDS", "ASSURANCE_LEVELS", "Actor", "CAPABILITY_ID_PATTERN", "EFFECT_ORDER", "FIXTURE_LABEL",
           "LIFECYCLES", "RECORD_SCHEMA_VERSION", "RegistryApproval", "RegistryPolicy", "Refusal",
           "TransitionFacts", "VERIFICATION_ASSURANCE", "assurance_at_least", "effect_above", "effective_effect",
           "expire_assurance", "iso", "measured_assurance", "new_record", "not_found", "parse_ref",
           "review_effect", "semver_key", "transition_record"]
