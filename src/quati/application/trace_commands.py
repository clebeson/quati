"""``quati trace show|explain`` in S00 (M26 Public interface, S00 form; LOG-0041 decision D6).

Read-only views over what S00 persists: the request receipt (``ask`` writes exactly one per
request) and the ``authz.decided`` / ``policy.decided`` events of the registry audit log. S00 has
no ledger: there is no commitment id, no ``audit_events`` row and no event id, and the answer
says so in ``not_recorded`` instead of inventing a value.

Order of checks: the caller is already authenticated (the context is a constructor argument);
then the AuthorizationPort decides and logs ``read`` on the tenant's registry before any record is
read; then the identifier is looked up among the caller's own receipts. A record of another
principal and an unknown identifier are the same NOT_FOUND. A receipt file or audit log that cannot
be read safely is ``audit_store_unavailable`` (exit 4, no fallback); an unsafe data directory is
refused by the storage adapter itself, like for every other command (``state_dir_unsafe``).

Display rule (S00 runtime contract): hashes, identifiers, enums, counts and timestamps only. A
receipt is an unsigned local file, so every displayed value is copied field by field through a
shape check; a field this module does not know is never shown, and a known field whose value has
another shape is withheld and named in ``uncertainties``. Request text and model-written text are
never displayed, not even when the receipt holds them (``--synthetic-evidence``).
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any, Callable

from quati.application.ask import DIGEST_FIELDS, RESULT_KINDS
from quati.application.discovery_tools import DISCOVERY_TOOLS
from quati.domain.capability_registry import Refusal

SOURCE = "S00_RECEIPTS_AND_REGISTRY_AUDIT_LOG"
INTEGRITY = "UNSIGNED_LOCAL_FILE"
REQUEST_ID = re.compile(r"request-[0-9a-f]{32}")
TRACE_ID = re.compile(r"[0-9a-f]{32}")
STATUSES = ("SUCCEEDED", "PARTIAL", "BLOCKED", "DENIED", "UNAVAILABLE", "CONFLICT")
OPERATIONS = ("search", "describe", "invoke", "status", "none_fits", "invalid")
VERDICTS = ("ALLOW", "DENY", "APPROVAL_REQUIRED")
PROOF_TIERS = ("L0", "L1", "L2", "L3", "L4", "L5")
# M26 ``excluded_reason`` for each S00 hard-filter reason (M15 filter order); the first class that applies wins.
SCOPE_REASONS = ("NOT_AUTHORIZED",)
POLICY_REASONS = ("EFFECT_ABOVE_CEILING", "DATA_CLASS_ABOVE_CEILING")
NOT_RECORDED = {"commitment_id": "commitments_arrive_in_slice_S02",
                "event_ids": "audit_events_table_arrives_in_slice_S02"}
RATIONALE_NOT_RECORDED = "model_text_is_never_displayed_in_S00"
RESULT_KIND_NOT_RECORDED = "receipt_kind_records_no_result_kind"


def _pattern(expression: str) -> Callable[[Any], bool]:
    compiled = re.compile(expression)
    return lambda value: isinstance(value, str) and compiled.fullmatch(value) is not None


def _one_of(*values: Any) -> Callable[[Any], bool]:
    return lambda value: isinstance(value, str) and value in values


def _integer(value: Any) -> bool:
    return type(value) is int and 0 <= value < 2 ** 53


def _number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _boolean(value: Any) -> bool:
    return type(value) is bool


HEX = _pattern(r"[0-9a-f]{64}")
CODE = _pattern(r"[A-Za-z_][A-Za-z0-9_]{0,63}")
TOKEN = _pattern(r"[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}")
CAPABILITY_ID = _pattern(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
VERSION = _pattern(r"[0-9A-Za-z][0-9A-Za-z.+-]{0,63}")
CAPABILITY_REF = _pattern(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}@[0-9A-Za-z][0-9A-Za-z.+-]{0,63}")
STEP_REF = _pattern(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}@[0-9A-Za-z][0-9A-Za-z.+-]{0,63}|sha256:[0-9a-f]{64}")
POLICY_REF = _pattern(r"[A-Za-z0-9_][A-Za-z0-9_./-]{0,127}@[0-9a-f]{64}")
FILTER_RESULT = _pattern(r"[A-Z_]{1,40}:[A-Z_]{1,20}")
TIMESTAMP = _pattern(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d{1,9})?(Z|[+-]\d\d:\d\d)")
DIGEST_CHECKS = {name: POLICY_REF if name == "policy_ref" else HEX for name in DIGEST_FIELDS}


class TraceStoreUnavailable(Exception):
    """Raised by the receipt reader port when a receipt file cannot be read as a private regular file."""


class _Copy:
    """Field-by-field copy of an untrusted record; remembers which known fields were withheld."""

    def __init__(self) -> None:
        self.withheld: set[str] = set()

    def take(self, source: Any, key: str, check: Callable[[Any], bool], label: str) -> Any:
        value = source.get(key) if isinstance(source, dict) else None
        if value is None or check(value):
            return value
        self.withheld.add(label)
        return None

    def items(self, source: Any, key: str, check: Callable[[Any], bool], label: str) -> list:
        value = source.get(key) if isinstance(source, dict) else None
        if value is None:
            return []
        if not isinstance(value, list) or not all(check(item) for item in value):
            self.withheld.add(label)
            return []
        return list(value)

    def group(self, source: Any, key: str) -> dict:
        value = source.get(key) if isinstance(source, dict) else None
        return value if isinstance(value, dict) else {}

    def records(self, source: Any, key: str, label: str) -> list[dict]:
        value = source.get(key) if isinstance(source, dict) else None
        if value is None:
            return []
        if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
            self.withheld.add(label)
            return []
        return value


def _response(status: str, data: Any, code: str | None = None, message: str | None = None,
              next_action: str | None = None, uncertainties: tuple | list = (), evidence_refs: tuple | list = ()) -> dict:
    return {"status": status, "data": data, "evidence_refs": list(evidence_refs),
            "uncertainties": list(uncertainties), "next_action": next_action,
            "error": None if code is None else {"code": code, "message": message, "retryable": False}}


def _not_found() -> tuple[int, dict]:
    return 4, _response("DENIED", {"reason": "trace_not_found"}, "NOT_FOUND",
                        "No recorded request of this principal has this request id or trace id.",
                        "Use the request_id or trace_id printed by `quati ask --json`; nothing was changed.")


def _store_unavailable() -> tuple[int, dict]:
    return 4, _response("UNAVAILABLE", {"reason": "audit_store_unavailable"}, "TEMPORARILY_UNAVAILABLE",
                        "The local receipts or the audit log cannot be read safely; nothing was shown.",
                        "Check that the Quati data directory, its receipts and capabilities directories and the "
                        "audit log are private files of this user (no symlink), then retry.")


def _ambiguous() -> tuple[int, dict]:
    return 4, _response("BLOCKED", {"reason": "receipt_ambiguous"}, "EVIDENCE_INSUFFICIENT",
                        "More than one local receipt claims this request; none is shown.",
                        "Compare the receipt files with the evidence reference printed by the original command.")


class TraceCommands:
    """``authorize(context, operation, action)`` is the registry enforcement point (it logs the decision
    and returns a refusal or None); ``receipts.find(identifier)`` and ``audit_events()`` raise when the
    store cannot be read safely (``TraceStoreUnavailable`` or the registry ``Refusal``)."""

    def __init__(self, *, context, authorize: Callable, receipts, audit_events: Callable[[], list]) -> None:
        self.context = context
        self.authorize = authorize
        self.receipts = receipts
        self.audit_events = audit_events

    # ------------------------------------------------------------------ lookup
    def _load(self, operation: str, identifier: str):
        """(None, receipt item, request events) or (refusal, None, None)."""
        blocked = self.authorize(self.context, f"trace_{operation}", "read")
        if blocked is not None:
            if blocked.code != "FORBIDDEN":
                return _store_unavailable(), None, None
            return (4, _response("DENIED", {"reason": blocked.reason}, "FORBIDDEN", blocked.reason,
                                 blocked.next_action)), None, None
        if not isinstance(identifier, str) or not (REQUEST_ID.fullmatch(identifier) or TRACE_ID.fullmatch(identifier)):
            return _not_found(), None, None
        try:
            found = self.receipts.find(identifier)
            events = self.audit_events()
        except (TraceStoreUnavailable, ValueError, Refusal):
            return _store_unavailable(), None, None
        principal = hashlib.sha256(self.context.actor_id.encode()).hexdigest()
        mine = [item for item in found if item["record"].get("principal_hash") == principal
                and _is(REQUEST_ID, item["record"].get("request_id")) and _is(TRACE_ID, item["record"].get("trace_id"))]
        if not mine:
            return _not_found(), None, None
        if len(mine) > 1:
            return _ambiguous(), None, None
        request_id = mine[0]["record"]["request_id"]
        related = [event for event in events if isinstance(event, dict) and event.get("request_id") == request_id
                   and event.get("tenant_id") == self.context.tenant_id
                   and event.get("actor_id") == self.context.actor_id]
        return None, mine[0], related

    # ------------------------------------------------------------------ show
    def show(self, identifier: str) -> tuple[int, dict]:
        refusal, item, events = self._load("show", identifier)
        if refusal is not None:
            return refusal
        copy = _Copy()
        shown, _catalog = _receipt_view(copy, item)
        record = item["record"]
        not_recorded = dict(NOT_RECORDED)
        if not isinstance(record.get("outcome"), dict):
            not_recorded["result_kind"] = RESULT_KIND_NOT_RECORDED
        data = {"request_id": record["request_id"], "trace_id": record["trace_id"], "commitment_id": None,
                "source": SOURCE, "receipt": shown, "authz_decisions": _authz_decisions(copy, events),
                "policy_decisions": _policy_decisions(copy, events), "not_recorded": not_recorded}
        return _answer(data, copy, [], item)

    # ------------------------------------------------------------------ explain
    def explain(self, identifier: str) -> tuple[int, dict]:
        refusal, item, events = self._load("explain", identifier)
        if refusal is not None:
            return refusal
        copy = _Copy()
        shown, catalog = _receipt_view(copy, item)
        record = item["record"]
        policies = _policy_decisions(copy, events)
        steps = shown["trajectory"]
        uncertainties = []
        selected_ref = next((step["capability_ref"] for step in steps
                             if step["operation"] == "invoke" and step["handler_executed"] is True
                             and step["status"] == "SUCCEEDED" and _is_ref(step["capability_ref"])), None)
        decision = next((entry for entry in policies if selected_ref is not None
                         and entry["capability_ref"] == selected_ref and entry["verdict"] == "ALLOW"), None)
        selected = None
        if selected_ref is None:
            uncertainties.append("no_capability_selected")
        else:
            capability_id, version = selected_ref.split("@", 1)
            selected = {"capability_id": capability_id, "version": version,
                        "binding_hash": None if decision is None else decision["binding_version"]}
        candidates, searched = _candidates(steps, catalog, selected)
        if searched and catalog is None:
            uncertainties.append("unranked_candidates_not_recorded")
        provider = shown["provider"]
        observed = provider["observed_model_ids"]
        data = {"request_id": record["request_id"], "trace_id": record["trace_id"], "commitment_id": None,
                "source": SOURCE, "selected": selected, "candidates": candidates,
                "executed_capabilities": shown["executed_capabilities"],
                "policy_decision_id": None if decision is None else decision["decision_id"],
                "model_id": observed[0] if len(observed) == 1 else None, "observed_model_ids": observed,
                "provider_id": provider["provider_id"],
                "effective_prompt_hash": shown["digests"]["effective_prompt_hash"],
                "model_rationale": None, "model_rationale_sha256": shown["final_text_sha256"], "event_ids": [],
                "receipt": {"ref": shown["ref"], "sha256": shown["sha256"], "integrity": INTEGRITY},
                "not_recorded": {**NOT_RECORDED, "model_rationale": RATIONALE_NOT_RECORDED}}
        return _answer(data, copy, uncertainties, item)


def _is(pattern: re.Pattern, value: Any) -> bool:
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _is_ref(value: Any) -> bool:
    return CAPABILITY_REF(value)


def _answer(data: dict, copy: _Copy, uncertainties: list, item: dict) -> tuple[int, dict]:
    notes = [*uncertainties, *(f"receipt_value_withheld:{label}" for label in sorted(copy.withheld))]
    return 0, _response("PARTIAL" if notes else "SUCCEEDED", data, uncertainties=notes, evidence_refs=[item["ref"]],
                        next_action=("Fields named in uncertainties are not in the S00 records or were withheld; "
                                     "nothing was changed.") if notes else None)


def _receipt_view(copy: _Copy, item: dict) -> tuple[dict, list[dict] | None]:
    """The displayable receipt and, when the receipt recorded it, the catalog (ids and lifecycle only)."""
    record = item["record"]
    outcome, digests = copy.group(record, "outcome"), copy.group(record, "digests")
    usage, provider = copy.group(record, "usage"), copy.group(record, "provider")
    tools = tuple(tool.name for tool in DISCOVERY_TOOLS)
    steps = []
    for step in copy.records(record, "trajectory", "trajectory"):
        excluded = [{"capability_id": copy.take(entry, "capability_id", CAPABILITY_ID, "trajectory.excluded"),
                     "capability_version": copy.take(entry, "capability_version", VERSION, "trajectory.excluded"),
                     "reasons": copy.items(entry, "reasons", CODE, "trajectory.excluded")}
                    for entry in copy.records(step, "excluded", "trajectory.excluded")]
        ranks = [{"bm25": copy.take(entry, "bm25", _number, "trajectory.rank_reasons"),
                  "filter_results": copy.items(entry, "filter_results", FILTER_RESULT, "trajectory.rank_reasons"),
                  "rank": copy.take(entry, "rank", _integer, "trajectory.rank_reasons"),
                  "shortlist_k": copy.take(entry, "shortlist_k", _integer, "trajectory.rank_reasons")}
                 for entry in copy.records(step, "rank_reasons", "trajectory.rank_reasons")]
        steps.append({
            "step": copy.take(step, "step", _integer, "trajectory.step"),
            "tool_name": copy.take(step, "tool_name", _one_of(*tools), "trajectory.tool_name"),
            "operation": copy.take(step, "operation", _one_of(*OPERATIONS), "trajectory.operation"),
            "status": copy.take(step, "status", _one_of(*STATUSES), "trajectory.status"),
            "result_code": copy.take(step, "result_code", CODE, "trajectory.result_code"),
            "reason": copy.take(step, "reason", CODE, "trajectory.reason"),
            "capability_ref": copy.take(step, "capability_ref", STEP_REF, "trajectory.capability_ref"),
            "binding_id": copy.take(step, "binding_id", TOKEN, "trajectory.binding_id"),
            "execution_id": copy.take(step, "execution_id", TOKEN, "trajectory.execution_id"),
            "handler_executed": copy.take(step, "handler_executed", _boolean, "trajectory.handler_executed"),
            "selection_error": copy.take(step, "selection_error", _boolean, "trajectory.selection_error"),
            "policy_verdict": copy.take(step, "policy_verdict", _one_of(*VERDICTS), "trajectory.policy_verdict"),
            "arguments_digest": copy.take(step, "arguments_digest", HEX, "trajectory.arguments_digest"),
            "result_sha256": copy.take(step, "result_sha256", HEX, "trajectory.result_sha256"),
            "candidate_ids": copy.items(step, "candidate_ids", CAPABILITY_ID, "trajectory.candidate_ids"),
            "excluded": excluded, "rank_reasons": ranks})
    shown = {
        "ref": item["ref"], "sha256": item["sha256"], "integrity": INTEGRITY,
        "kind": copy.take(record, "kind", CODE, "kind"), "scope": copy.take(record, "scope", CODE, "scope"),
        "timestamp": copy.take(record, "timestamp", TIMESTAMP, "timestamp"),
        "evidence_version": copy.take(record, "evidence_version", _pattern(r"[a-z0-9]{1,16}/[0-9]{1,6}"),
                                      "evidence_version"),
        "status": copy.take(record, "status", _one_of(*STATUSES), "status"),
        "result_kind": copy.take(outcome, "result_kind", _one_of(*RESULT_KINDS), "outcome.result_kind"),
        "reason": copy.take(outcome, "reason", CODE, "outcome.reason"),
        "executed_capabilities": copy.items(outcome, "executed_capabilities", CAPABILITY_REF,
                                            "outcome.executed_capabilities"),
        "proof_tier": copy.take(record, "proof_tier", _one_of(*PROOF_TIERS), "proof_tier"),
        "provider_used": copy.take(record, "provider_used", _boolean, "provider_used"),
        "policy_version": copy.take(record, "policy_version", _pattern(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}"),
                                    "policy_version"),
        "request_hash": copy.take(record, "request_hash", HEX, "request_hash"),
        "output_hash": copy.take(record, "output_hash", HEX, "output_hash"),
        "final_text_sha256": copy.take(record, "final_text_sha256", HEX, "final_text_sha256"),
        "classification_sha256": copy.take(record, "classification_sha256", HEX, "classification_sha256"),
        "catalog_access": copy.take(record, "catalog_access", CODE, "catalog_access"),
        "digests": {name: copy.take(digests, name, check, f"digests.{name}") for name, check in DIGEST_CHECKS.items()},
        "usage": {"model_requests": copy.take(usage, "model_requests", _integer, "usage.model_requests"),
                  "input_tokens": copy.take(usage, "input_tokens", _integer, "usage.input_tokens"),
                  "output_tokens": copy.take(usage, "output_tokens", _integer, "usage.output_tokens"),
                  "cost_usd": copy.take(usage, "cost_usd", _number, "usage.cost_usd")},
        "provider": {"provider_id": copy.take(provider, "provider_id", TOKEN, "provider.provider_id"),
                     "transport": copy.take(provider, "transport", TOKEN, "provider.transport"),
                     "configured_model": copy.take(provider, "configured_model", TOKEN, "provider.configured_model"),
                     "observed_model_ids": copy.items(provider, "observed_model_ids", TOKEN,
                                                      "provider.observed_model_ids"),
                     "model_digest": copy.take(provider, "model_digest", HEX, "provider.model_digest"),
                     "model_identity_source": copy.take(provider, "model_identity_source", CODE,
                                                        "provider.model_identity_source")},
        "synthetic_evidence_recorded": isinstance(record.get("synthetic_evidence"), dict),
        "trajectory": steps}
    catalog = None
    synthetic = record.get("synthetic_evidence")
    if isinstance(synthetic, dict) and synthetic.get("catalog") is not None:
        catalog = [{"capability_id": copy.take(entry, "capability_id", CAPABILITY_ID, "synthetic_evidence.catalog"),
                    "capability_version": copy.take(entry, "capability_version", VERSION, "synthetic_evidence.catalog")}
                   for entry in copy.records(synthetic, "catalog", "synthetic_evidence.catalog")]
    return shown, catalog


def _authz_decisions(copy: _Copy, events: list[dict]) -> list[dict]:
    decisions = []
    for event in events:
        if event.get("event") != "authz.decided":
            continue
        decision = copy.group(event, "decision")
        decisions.append({
            "operation": copy.take(event, "operation", CODE, "audit.authz.operation"),
            "action": copy.take(decision, "action", CODE, "audit.authz.action"),
            "verdict": copy.take(decision, "verdict", _one_of(*VERDICTS), "audit.authz.verdict"),
            "reason_code": copy.take(decision, "reason_code", CODE, "audit.authz.reason_code"),
            "resource_ref": copy.take(decision, "resource_ref", TOKEN, "audit.authz.resource_ref"),
            "owner_space_id": copy.take(event, "owner_space_id", TOKEN, "audit.authz.owner_space_id"),
            "at": copy.take(event, "at", TIMESTAMP, "audit.authz.at")})
    return decisions


def _policy_decisions(copy: _Copy, events: list[dict]) -> list[dict]:
    decisions = []
    for event in events:
        if event.get("event") != "policy.decided":
            continue
        decision, intent = copy.group(event, "decision"), copy.group(event, "intent")
        capability_id = copy.take(event, "capability_id", CAPABILITY_ID, "audit.policy.capability_id")
        version = copy.take(event, "capability_version", VERSION, "audit.policy.capability_version")
        decisions.append({
            "decision_id": copy.take(decision, "decision_id", TOKEN, "audit.policy.decision_id"),
            "verdict": copy.take(decision, "verdict", _one_of(*VERDICTS), "audit.policy.verdict"),
            "reason_code": copy.take(decision, "reason_code", TOKEN, "audit.policy.reason_code"),
            "matched_rule_ids": copy.items(decision, "matched_rule_ids", TOKEN, "audit.policy.matched_rule_ids"),
            "policy_version": copy.take(decision, "policy_version", TOKEN, "audit.policy.policy_version"),
            "intent_digest": copy.take(decision, "intent_digest", HEX, "audit.policy.intent_digest"),
            "capability_ref": None if capability_id is None or version is None else f"{capability_id}@{version}",
            "effect_id": copy.take(event, "effect_id", TOKEN, "audit.policy.effect_id"),
            "effect_class": copy.take(intent, "effect_class", CODE, "audit.policy.effect_class"),
            "binding_id": copy.take(intent, "binding_id", TOKEN, "audit.policy.binding_id"),
            "binding_version": copy.take(intent, "binding_version", HEX, "audit.policy.binding_version"),
            "at": copy.take(event, "at", TIMESTAMP, "audit.policy.at")})
    return decisions


def _excluded_reason(reasons: list[str]) -> str:
    if any(reason in SCOPE_REASONS for reason in reasons):
        return "scope_not_granted"
    if any(reason in POLICY_REASONS for reason in reasons):
        return "policy_denied"
    return "capability_unavailable"


def _candidates(steps: list[dict], catalog: list[dict] | None, selected: dict | None) -> tuple[list[dict], bool]:
    """Every candidate the recorded searches considered, sorted by capability id, and whether a search ran.

    Ranked candidates come from the search steps (``rank_features`` is the recorded rank entry),
    filtered ones from the recorded ``excluded`` lists, and - only when the receipt recorded the
    catalog - eligible entries that no search returned (``outcome_mismatch``).
    """
    versions: dict[str, str] = {}
    for step in steps:
        if _is_ref(step["capability_ref"]):
            capability_id, version = step["capability_ref"].split("@", 1)
            versions.setdefault(capability_id, version)
    found: dict[str, dict] = {}
    searched = False
    for step in steps:
        if step["operation"] != "search" or step["status"] != "SUCCEEDED":
            continue
        searched = True
        aligned = len(step["rank_reasons"]) == len(step["candidate_ids"])
        for position, capability_id in enumerate(step["candidate_ids"]):
            chosen = selected is not None and selected["capability_id"] == capability_id
            found.setdefault(capability_id, {
                "capability_id": capability_id, "version": versions.get(capability_id),
                "rank_features": step["rank_reasons"][position] if aligned else None, "authorization": "ALLOW",
                "excluded_reason": None if chosen else "lower_rank", "filter_reasons": []})
        for entry in step["excluded"]:
            if entry["capability_id"] is None:
                continue
            denied = any(reason in SCOPE_REASONS + POLICY_REASONS for reason in entry["reasons"])
            found.setdefault(entry["capability_id"], {
                "capability_id": entry["capability_id"], "version": entry["capability_version"],
                "rank_features": None, "authorization": "DENY" if denied else "ALLOW",
                "excluded_reason": _excluded_reason(entry["reasons"]), "filter_reasons": list(entry["reasons"])})
    if searched and catalog is not None:
        for entry in catalog:
            if entry["capability_id"] is not None:
                ranked = found.get(entry["capability_id"])
                if ranked is not None and ranked["version"] is None and ranked["rank_features"] is not None:
                    ranked["version"] = entry["capability_version"]
                found.setdefault(entry["capability_id"], {
                    "capability_id": entry["capability_id"], "version": entry["capability_version"],
                    "rank_features": None, "authorization": "ALLOW", "excluded_reason": "outcome_mismatch",
                    "filter_reasons": []})
    return [found[key] for key in sorted(found)], searched


__all__ = ["TraceCommands", "TraceStoreUnavailable"]
