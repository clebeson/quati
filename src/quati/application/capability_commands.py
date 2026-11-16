"""Operator capability commands (M14 CLI): install, install-fixture, list, search, describe, disable.

Every command first passes the AuthorizationPort for the authenticated operator (reads need a
grant on the space that owns the tenant's registry; install, enable and disable also need the
OWNER or ADMIN tenant role) and its decision is logged as ``authz.decided``; a denied command
reads and changes nothing and writes no receipt. Every change writes one evidence receipt holding
the registry audit events it produced (activation included). Search and describe run through the
same DiscoveryPort guards as the model. Exit codes follow M14/M01: 0 ok, 2 invalid input,
3 missing configuration, 4 denied/unavailable/blocked/conflict, 5 provider failure, 1 internal.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from quati.domain.capability_registry import Refusal

NEXT_ACTIONS = {
    "BLOCKED": "Correct the package or its activation; nothing was enabled.",
    "DENIED": "Use an authorized operator and an effect within the S00 read ceiling; nothing was enabled.",
    "UNAVAILABLE": "The capability is not available; nothing was changed.",
    "CONFLICT": "Inspect the installed version and retry with a new version; nothing was changed.",
}


def _exit(value: dict) -> int:
    if value["status"] in ("SUCCEEDED", "PARTIAL"):
        return 0
    code = (value.get("error") or {}).get("code")
    if code == "INTERNAL_ERROR":
        return 1
    if code in ("INVALID_INPUT", "CONFIG_INVALID", "SCHEMA_INVALID"):
        return 2
    if code == "NOT_CONFIGURED":
        return 3
    if code in ("TEMPORARILY_UNAVAILABLE", "DEADLINE_EXCEEDED", "OUTPUT_INVALID"):
        return 5
    return 4


def _complete(value: dict) -> dict:
    if value["status"] in NEXT_ACTIONS and not value.get("next_action"):
        value["next_action"] = NEXT_ACTIONS[value["status"]]
    return value


class CapabilityCommands:
    def __init__(self, *, context, registry, discovery, evidence_sink: Callable[[dict], dict],
                 write_fixture_package: Callable[[str], Path], fixture_names: tuple[str, ...]) -> None:
        self.context = context
        self.registry = registry
        self.discovery = discovery
        self.evidence_sink = evidence_sink
        self.write_fixture_package = write_fixture_package
        self.fixture_names = fixture_names

    # ------------------------------------------------------------- changes
    def _recorded(self, operation: str, value: dict, audit_before: int) -> tuple[int, dict]:
        events = self.registry.store.audit_events()[audit_before:]
        receipt = self.evidence_sink({"kind": "capability_command", "operation": operation,
                                      "actor_id": self.context.actor_id, "tenant_id": self.context.tenant_id,
                                      "request_id": self.context.request_id, "status": value["status"],
                                      "data": value["data"], "audit_events": events})
        value["evidence_refs"] = [f"sha256:{receipt['sha256']}:{receipt['path']}"]
        return _exit(value), _complete(value)

    def _audit_size(self) -> int:
        return len(self.registry.store.audit_events())

    def _denied(self, operation: str, action: str) -> tuple[int, dict] | None:
        """RFC-013 section 6: the AuthorizationPort decides, and logs, before any registry read or change."""
        blocked = self.discovery.authorize(self.context, operation, action)
        if blocked is None:
            return None
        value = blocked.to_response()
        return _exit(value), _complete(value)

    def install(self, path: str, *, fixture_handler: str | None = None, enable_fixture: bool = False,
                source: str | None = None) -> tuple[int, dict]:
        denied = self._denied("install", "manage")
        if denied is not None:
            return denied
        before = self._audit_size()
        package = Path(path)
        value = self.registry.install(self.context, package, source=source or f"file://{package.resolve()}",
                                      fixture_handler=fixture_handler, enable_fixture=enable_fixture)
        return self._recorded("install", value, before)

    def install_fixture(self, name: str, *, enable_fixture: bool = False) -> tuple[int, dict]:
        denied = self._denied("install_fixture", "manage")
        if denied is not None:
            return denied
        if name not in self.fixture_names:
            return 2, _response("DENIED", {"reason": "FIXTURE_UNKNOWN", "fixtures": list(self.fixture_names)},
                                "INVALID_INPUT", "FIXTURE_UNKNOWN", "Choose one of the listed public fixtures.")
        before = self._audit_size()
        value = self.registry.install(self.context, self.write_fixture_package(name), source=f"fixture:{name}",
                                      fixture_handler=name, enable_fixture=enable_fixture, import_kind="fixture")
        return self._recorded("install_fixture", value, before)

    def disable(self, ref: str) -> tuple[int, dict]:
        denied = self._denied("disable", "manage")
        if denied is not None:
            return denied
        before = self._audit_size()
        try:
            record = self.registry.record(self.context, ref)
            updated = self.registry.transition(self.context, ref, record["revision"], "DISABLED")
        except Refusal as exc:
            value = _response(exc.status, {"definition_ref": ref, "reason": exc.reason}, exc.code, exc.reason)
        else:
            value = _response("SUCCEEDED", {"definition_ref": ref, "lifecycle": updated["lifecycle"]})
        return self._recorded("disable", value, before)

    # ------------------------------------------------------------- reads
    def list(self, *, enabled_only: bool = False) -> tuple[int, dict]:
        denied = self._denied("list", "read")
        if denied is not None:
            return denied
        items = [{"definition_ref": f"{item['capability_id']}@{item['capability_version']}",
                  "capability_id": item["capability_id"], "capability_version": item["capability_version"],
                  "lifecycle": item["lifecycle"], "assurance": item["assurance"], "source": item["source"],
                  "package_sha256": item["package_sha256"]}
                 for item in self.registry.records(self.context, enabled_only=enabled_only)]
        return 0, _response("SUCCEEDED", {"capabilities": items})

    def search(self, query: str) -> tuple[int, dict]:
        result = self.discovery.begin_turn(self.context).search(self.context, query)
        value = result.to_response()
        return _exit(value), _complete(value)

    def describe(self, capability_id: str) -> tuple[int, dict]:
        turn = self.discovery.begin_turn(self.context)
        result = turn.describe(self.context, capability_id)
        value = result.to_response()
        return _exit(value), _complete(value)


def _response(status: str, data: Any, code: str | None = None, message: str | None = None,
              next_action: str | None = None) -> dict:
    return _complete({"status": status, "data": data, "evidence_refs": [], "uncertainties": [],
                      "next_action": next_action,
                      "error": None if code is None else {"code": code, "message": message, "retryable": False}})


__all__ = ["CapabilityCommands"]
