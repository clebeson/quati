"""DiscoveryPort use cases (M15): search, describe, invoke and status over the registry,
with the trusted policy gate before any handler runs (M25-FR-03).

The principal, tenant and space always come from the authenticated RequestContext of
the turn; model-supplied arguments are only the capability input and are validated
against the definition's input schema.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

import jsonschema

from quati.domain.canonical import digest
from quati.domain.capability_registry import Refusal, iso
from quati.domain.discovery import (
    EFFECTIVE_SHORTLIST_K, MAX_BINDING_FALLBACKS, MAX_TOOL_CALLS_PER_TURN, QUERY_MAX_CHARS, REFUSALS, REPORT_NO_CAPABILITY,
    CatalogEntry, ScopeGrant, SearchScope, clamp_limit, filter_reasons, is_capability_id, latest_per_id,
    query_terms, rank, rank_reasons)
from quati.domain.policy import EffectIntent

FIXTURE_RESULT = "FIXTURE_RESULT"
HIDDEN_LIFECYCLES = ("DRAFT", "VALIDATED", "STAGED")
# M02 reason table, LOCAL row NO_SPACE_GRANT / ROLE_INSUFFICIENT (the command is delivered in slice S02).
SPACE_GRANT_NEXT_ACTION = ("Inspect the space grant with `quati spaces describe <space-id>` (delivered in slice S02); "
                           "nothing was read or changed.")


@dataclass
class PortResult:
    status: str
    code: str | None = None
    reason: str | None = None
    data: Any = None
    next_action: str | None = None
    uncertainties: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    trace: dict = field(default_factory=dict)

    def to_response(self) -> dict:
        return {"status": self.status, "data": self.data, "evidence_refs": list(self.evidence_refs),
                "uncertainties": list(self.uncertainties), "next_action": self.next_action,
                "error": None if self.code is None else {"code": self.code, "message": self.reason,
                                                         "retryable": self.code == "TEMPORARILY_UNAVAILABLE"}}


def refused(reason: str, **trace: Any) -> PortResult:
    status, code = REFUSALS[reason]
    return PortResult(status, code, reason, {"reason": reason}, trace={"handler_executed": False, **trace})


def build_effect_intent(context, grant: ScopeGrant, *, capability_id: str, capability_version: str,
                        binding_id: str, binding_version: str, effect_class: str, destinations: tuple[str, ...],
                        arguments: Mapping[str, Any], idempotency_key: str, effect_id: str,
                        policy_version: str) -> EffectIntent:
    """Every field from trusted code; capability input is UNTRUSTED and steers only none/read effects."""
    return EffectIntent(
        effect_id=effect_id, actor_id=context.actor_id, tenant_id=context.tenant_id, capability_id=capability_id,
        capability_version=capability_version, binding_id=binding_id, binding_version=binding_version,
        operation="invoke", destination_ref=destinations[0] if destinations else
        f"capability:{capability_id}@{capability_version}", policy_version=policy_version,
        idempotency_key=idempotency_key, input_digest=digest(dict(arguments)), effect_class=effect_class,
        data_class=grant.input_data_class, integrity="UNTRUSTED",
        steering_args_user_confirmed=effect_class in ("none", "read"), space_id=grant.space_id,
        space_kind=grant.space_kind)


def _valid(instance: Any, schema: Mapping[str, Any]) -> bool:
    try:
        jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(instance)
    except Exception:  # noqa: BLE001 - any validator failure is a mismatch
        return False
    return True


class DiscoveryService:
    def __init__(self, registry, index, handlers, *, policy_gate, grants, clock: Callable, ids: Callable[[str], str],
                 authorization, audit: Callable[[dict], None] | None = None, effect_ceiling: str = "read") -> None:
        # The AuthorizationPort is required (RFC-013 1<=>N rule): there is no fallback and no grant is
        # ever derived from the request. A falsy port object is still the port.
        if authorization is None:
            raise TypeError("DiscoveryService requires an AuthorizationPort")
        self.authorization = authorization
        self.registry = registry
        self.index = index
        self.handlers = handlers
        self.policy_gate = policy_gate
        self.grants = grants
        self.clock = clock
        self.ids = ids
        self.audit_sink = audit or registry.store.append_audit
        self.effect_ceiling = effect_ceiling
        self.executions: dict[str, dict] = {}
        self.idempotency: dict[str, str] = {}

    def begin_turn(self, context, *, model_features=None, require_describe: bool = False) -> "DiscoveryTurn":
        features = None if model_features is None else frozenset(model_features)
        return DiscoveryTurn(self, context, features, require_describe=require_describe)

    def audit(self, event: dict) -> None:
        self.audit_sink({"at": iso(self.clock()), **event})

    def authorize(self, context, operation: str, action: str = "read") -> PortResult | None:
        """The single enforcement point of every registry operation (RFC-013 section 6 and section 12,
        S00 row; M02 authorization order rows 4 and 7), before any registry lookup or change.

        The resource is the tenant's capability registry; the port resolves the space that OWNS it
        from the directory, never from the request. ``action`` is ``read`` (list, search, describe,
        invoke, status, the ask receipt's catalog digest) or ``manage`` (install, enable, disable).
        The decision and the scope it was evaluated against are logged for the allowed and the
        denied operation alike; an operation whose decision cannot be logged is refused.
        """
        evaluation = self.authorization.decide(context, action, f"registry:{context.tenant_id}")
        decision, scope = evaluation.decision, evaluation.scope
        try:
            self.audit({"event": "authz.decided", "operation": operation, "decision": decision.to_json(),
                        "authorized_scope": None if scope is None else scope.to_json(),
                        "owner_space_id": evaluation.space_id, "actor_id": context.actor_id,
                        "tenant_id": context.tenant_id, "request_id": context.request_id})
            logged = True
        except Exception:  # noqa: BLE001 - an audit failure refuses the operation
            logged = False
        if decision.verdict != "ALLOW":
            return PortResult("DENIED", "FORBIDDEN", decision.reason_code, {"reason": decision.reason_code},
                              next_action=SPACE_GRANT_NEXT_ACTION, trace={"handler_executed": False})
        return None if logged else refused("audit_unavailable")


class DiscoveryTurn:
    """One model turn: a tool-call budget, an accumulated shortlist and the turn's context."""

    def __init__(self, service: DiscoveryService, context, model_features, *, require_describe: bool = False) -> None:
        self.service = service
        self.context = context
        self.model_features = model_features
        # The model turn of ``quati ask`` (the operator commands leave it False). S00-T04 R4: an invoke
        # of a shortlisted id that passed guards 4-6 but was not described in this turn is refused with
        # DESCRIBE_REQUIRED before argument validation. LOG-0041 D4: ``describe`` answers only for an
        # id in this turn's shortlist, with the same single reason as ``invoke`` for any other id.
        self.require_describe = require_describe
        self.described: set[str] = set()
        self.shortlist: dict[str, str] = {}
        self.calls = 0
        self.executions_created = 0
        self.steps = 0

    # ------------------------------------------------------------------ shared
    def _scope(self) -> SearchScope:
        return SearchScope(self.service.grants.resolve(self.context), effect_ceiling=self.service.effect_ceiling,
                           model_features=self.model_features)

    def admit(self, context) -> PortResult | None:
        """Context binding, then the per-turn tool-call budget; every call counts."""
        ours = self.context
        if (context.actor_id, context.tenant_id, context.request_id) != (ours.actor_id, ours.tenant_id,
                                                                         ours.request_id):
            return refused("CONTEXT_MISMATCH")
        self.calls += 1
        if self.calls > MAX_TOOL_CALLS_PER_TURN:
            return refused("BUDGET_EXCEEDED")
        return None

    def authorize(self, operation: str) -> PortResult | None:
        """A read of the turn's registry, authorized for the turn's own context (never the caller's)."""
        return self.service.authorize(self.context, operation)

    def _selection_error(self, capability_id: str) -> PortResult:
        """LOG-0041 D4: the one ``invoke`` refusal for every id that this turn's searches did not
        return, whether it is unknown, malformed, hidden, disabled or enabled. The registry is not
        consulted, so the answer cannot tell the model which ids exist. Recorded as
        ``discovery.selection_error``; a well-formed id is logged as given, anything else only as
        its digest (model-written text never lands verbatim in the audit log)."""
        reference = capability_id if is_capability_id(capability_id) else "sha256:" + digest(capability_id)
        self.service.audit({"event": "discovery.selection_error", "capability_id": reference,
                            "reason": "NOT_IN_SHORTLIST", "actor_id": self.context.actor_id,
                            "request_id": self.context.request_id})
        return refused("NOT_IN_SHORTLIST", selection_error=True)

    def _entries(self, capability_id: str) -> tuple[list[CatalogEntry], Any]:
        snapshot = self.service.registry.catalog(self.context)
        return [entry for entry in snapshot.entries if entry.capability_id == capability_id], snapshot

    # ------------------------------------------------------------------ search
    def search(self, context, query: Any, limit: Any = None) -> PortResult:
        blocked = self.admit(context) or self.authorize("search")
        if blocked is not None:
            return blocked
        if not isinstance(query, str) or not query.strip():
            return refused("TOOL_CALL_MALFORMED")
        if len(query) > QUERY_MAX_CHARS:
            return refused("QUERY_TOO_LONG")
        scope = self._scope()
        snapshot = self.service.registry.catalog(self.context)
        survivors, excluded = [], []
        for entry in snapshot.entries:
            reasons = filter_reasons(entry, scope)
            if reasons:
                excluded.append({"capability_id": entry.capability_id,
                                 "capability_version": entry.capability_version, "reasons": list(reasons)})
            else:
                survivors.append(entry)
        survivors = latest_per_id(survivors)
        terms = query_terms(query)
        scores = self.service.index.score({entry.key: entry.search_text for entry in survivors}, terms)
        shortlist_k = clamp_limit(limit)
        ranked = rank(survivors, scores, shortlist_k)
        candidates = []
        for position, (entry, bm25) in enumerate(ranked, start=1):
            if entry.capability_id not in self.shortlist and len(self.shortlist) < EFFECTIVE_SHORTLIST_K:
                self.shortlist[entry.capability_id] = entry.capability_version
            candidates.append({"capability_id": entry.capability_id, "capability_version": entry.capability_version,
                               "name": entry.manifest["name"], "outcome_summary": entry.manifest["description"],
                               "effects": entry.enforced_effect, "rank": position,
                               "rank_reasons": rank_reasons(position, bm25, shortlist_k)})
        empty = not candidates
        return PortResult("SUCCEEDED", data={"candidates": candidates, "excluded": excluded},
                          next_action=REPORT_NO_CAPABILITY if empty else None,
                          uncertainties=("NO_CANDIDATES",) if empty else (),
                          trace={"handler_executed": False, "terms": list(terms)})

    # ------------------------------------------------------------------ describe
    def describe(self, context, capability_id: Any) -> PortResult:
        blocked = self.admit(context) or self.authorize("describe")
        if blocked is not None:
            return blocked
        if not isinstance(capability_id, str):
            return refused("TOOL_CALL_MALFORMED")
        if self.require_describe and capability_id not in self.shortlist:
            return refused("NOT_IN_SHORTLIST")      # D4: the same answer whatever the id is; nothing is read
        entries, _snapshot = self._entries(capability_id) if is_capability_id(capability_id) else ([], None)
        visible = [entry for entry in entries if entry.lifecycle not in HIDDEN_LIFECYCLES]
        if not visible:
            return refused("NOT_A_CAPABILITY_ID")
        version = self.shortlist.get(capability_id)
        chosen = next((entry for entry in visible if entry.capability_version == version), None) or max(
            visible, key=lambda entry: tuple(int(part) for part in entry.capability_version.split(".")))
        reasons = filter_reasons(chosen, self._scope())
        if reasons:
            return refused(reasons[0], capability_ref=chosen.key)
        manifest = chosen.manifest
        definition = {name: copy.deepcopy(manifest[name]) for name in (
            "name", "description", "intents", "input_schema", "output_schema", "outcomes", "effects", "permissions")}
        record = self.service.registry.record(self.context, chosen.key)
        self.described.add(chosen.key)
        return PortResult("SUCCEEDED", data={
            "capability_id": chosen.capability_id, "capability_version": chosen.capability_version,
            "definition": definition,
            "registry": {"lifecycle": record["lifecycle"], "assurance": record["assurance"],
                         "effect_class_reviewed": record["effect_class_reviewed"]}},
            trace={"handler_executed": False, "capability_ref": chosen.key})

    # ------------------------------------------------------------------ invoke
    def invoke(self, context, capability_id: Any, arguments: Any, idempotency_key: str | None = None) -> PortResult:
        blocked = self.admit(context) or self.authorize("invoke")
        if blocked is not None:
            return blocked
        service = self.service
        if not isinstance(capability_id, str) or not isinstance(arguments, Mapping):           # 1
            return refused("TOOL_CALL_MALFORMED")
        if capability_id not in self.shortlist:                                                 # 2-3
            return self._selection_error(capability_id)
        entries, snapshot = self._entries(capability_id)
        version = self.shortlist[capability_id]
        key = f"{capability_id}@{version}"
        entry = next((item for item in entries if item.capability_version == version), None)
        if entry is None or entry.lifecycle != "ENABLED":                                       # 4
            return refused("NOT_ENABLED", capability_ref=key)
        if not entry.loadable:
            return refused("DIGEST_MISMATCH", capability_ref=key)
        scope = self._scope()
        reasons = [reason for reason in filter_reasons(entry, scope) if reason != "BINDING_UNHEALTHY"]
        if "MODEL_INCOMPATIBLE" in reasons:                                                     # 5
            return refused("MODEL_INCOMPATIBLE", capability_ref=key)
        if reasons:                                                                             # 6
            return refused(reasons[0], capability_ref=key)
        if self.require_describe and key not in self.described:                                # 6b (ask only)
            # After every real guard (so their reasons are never masked), before argument validation.
            result = refused("DESCRIBE_REQUIRED", capability_ref=key)
            result.next_action = ("Call quati_describe with this capability_id first, then call quati_invoke "
                                  "with input that matches its input_schema.")
            return result
        arguments = dict(arguments)
        if not _valid(arguments, entry.manifest["input_schema"]):                              # 7
            return refused("ARGUMENTS_SCHEMA_INVALID", capability_ref=key)
        input_digest = digest(arguments)
        idempotency = digest({"tenant_id": self.context.tenant_id, "actor_id": self.context.actor_id,
                              "request_id": self.context.request_id, "capability": key, "input": input_digest,
                              "key": idempotency_key})
        bindings = list(snapshot.bindings[key])
        eligible = [item for item in bindings[: 1 + MAX_BINDING_FALLBACKS] if item["healthy"]]   # 9 (pre-policy)
        selected = next((item for item in eligible if service.handlers.resolve(item["handler"]) is not None), None)
        if selected is None:
            execution = self._new_execution(capability_id, version, None)
            execution.update(state="FAILED", reason="BINDING_UNAVAILABLE")
            return self._execution_result(execution, handler_executed=False, extra={"capability_ref": key})
        intent = build_effect_intent(
            self.context, scope.grant, capability_id=capability_id, capability_version=version,
            binding_id=selected["binding"]["id"], binding_version=selected["binding_sha256"],
            effect_class=entry.enforced_effect, destinations=tuple(entry.manifest.get("destinations", ())),
            arguments=arguments, idempotency_key=idempotency, effect_id=service.ids("effect"),
            policy_version=service.policy_gate.policy_version())
        decision = service.policy_gate.decide(self.context, intent)                             # 8
        trace = {"capability_ref": key, "policy_verdict": decision.verdict,
                 "narrowed_scope": None if decision.narrowed_scope is None else dict(decision.narrowed_scope)}
        try:
            service.audit({"event": "policy.decided", "decision": decision.to_json(), "effect_id": intent.effect_id,
                           "capability_id": capability_id, "capability_version": version,
                           "actor_id": self.context.actor_id, "tenant_id": self.context.tenant_id,
                           "request_id": self.context.request_id, "intent": intent.to_wire()})
            audited = True
        except Exception:  # noqa: BLE001 - an audit failure refuses dispatch
            audited = False
        if decision.verdict == "DENY":
            return PortResult("DENIED", "FORBIDDEN", decision.reason_code, {"reason": decision.reason_code},
                              trace={"handler_executed": False, **trace})
        if decision.verdict != "ALLOW":
            return PortResult("BLOCKED", "APPROVAL_REQUIRED", decision.reason_code, {"reason": decision.reason_code},
                              trace={"handler_executed": False, **trace})
        if not audited:
            return refused("audit_unavailable", **trace)
        scope_granted = decision.narrowed_scope
        if scope_granted is None:
            return refused("narrowed_scope_missing", **trace)
        expected = {"effect_id": intent.effect_id, "capability_id": capability_id, "operation": intent.operation,
                    "destination_ref": intent.destination_ref}
        if (any(scope_granted.get(name) != value for name, value in expected.items())
                or decision.intent_digest != digest(intent.to_wire())):    # decision bound to this binding id/sha
            return refused("narrowed_scope_violation", **trace)
        if idempotency in service.idempotency:                                    # replay, only after policy ALLOW
            execution = service.executions[service.idempotency[idempotency]]
            return self._execution_result(execution, handler_executed=False, extra=trace)
        execution = self._new_execution(capability_id, version, decision.decision_id)
        service.idempotency[idempotency] = execution["execution_id"]
        handler = selected["handler"]
        execution["binding_id"] = selected["binding"]["id"]
        try:
            output = service.handlers.execute(handler, arguments, now=service.clock())
        except Exception:  # noqa: BLE001 - a failing handler is a typed failure, never success
            execution.update(state="FAILED", reason="HANDLER_FAILED")
            return self._execution_result(execution, handler_executed=True, extra=trace)
        if not _valid(output, entry.manifest["output_schema"]):                                 # 10
            execution.update(state="FAILED", reason="RESULT_SCHEMA_INVALID")
            return self._execution_result(execution, handler_executed=True, extra=trace)
        mode = entry.manifest.get("outcome_verification", {"mode": "none"})["mode"]              # 11
        refs = output.get("evidence_refs", []) if isinstance(output, Mapping) else []
        trusted = set(service.handlers.resolve(handler).evidence_refs)
        if mode == "none":
            verification = "NOT_REQUIRED"
        elif mode == "evidence_check" and refs and set(refs) <= trusted:
            verification = "VERIFIED"
        else:
            verification = "UNVERIFIED"
        execution.update(state="SUCCEEDED", output=output, outcome_verification=verification,
                         evidence_refs=list(refs), reason="OUTCOME_UNVERIFIED" if verification == "UNVERIFIED"
                         else None)
        return self._execution_result(execution, handler_executed=True, extra=trace)

    def _new_execution(self, capability_id: str, version: str, decision_id: str | None) -> dict:
        service = self.service
        execution = {"execution_id": service.ids("execution"), "actor_id": self.context.actor_id,
                     "tenant_id": self.context.tenant_id, "capability_id": capability_id,
                     "capability_version": version, "state": "RUNNING", "reason": None, "output": None,
                     "binding_id": None, "commitment_ref": None, "outcome_verification": None,
                     "evidence_refs": [], "decision_id": decision_id}
        service.executions[execution["execution_id"]] = execution
        self.executions_created += 1
        return execution

    def _execution_result(self, execution: dict, *, handler_executed: bool, extra: Mapping | None = None) -> PortResult:
        trace = {"capability_ref": f"{execution['capability_id']}@{execution['capability_version']}",
                 **(extra or {}), "handler_executed": handler_executed, "execution_id": execution["execution_id"],
                 "binding_id": execution["binding_id"]}
        if execution["state"] == "FAILED":
            result = refused(execution["reason"], **trace)
            result.data = {"reason": execution["reason"], "execution_id": execution["execution_id"]}
            return result
        data = {"execution_id": execution["execution_id"], "capability_id": execution["capability_id"],
                "capability_version": execution["capability_version"], "result_label": FIXTURE_RESULT,
                "output": copy.deepcopy(execution["output"]),
                "outcome_verification": execution["outcome_verification"]}
        if execution["reason"] == "OUTCOME_UNVERIFIED":
            status, code = REFUSALS["OUTCOME_UNVERIFIED"]
            return PortResult(status, code, "OUTCOME_UNVERIFIED", data, evidence_refs=tuple(execution["evidence_refs"]),
                              uncertainties=("OUTCOME_UNVERIFIED",), trace=trace)
        return PortResult("SUCCEEDED", data=data, evidence_refs=tuple(execution["evidence_refs"]), trace=trace)

    # ------------------------------------------------------------------ status
    def status(self, context, execution_id: Any) -> PortResult:
        blocked = self.admit(context) or self.authorize("status")
        if blocked is not None:
            return blocked
        execution = self.service.executions.get(execution_id) if isinstance(execution_id, str) else None
        if execution is None or (execution["actor_id"], execution["tenant_id"]) != (self.context.actor_id,
                                                                                    self.context.tenant_id):
            return refused("EXECUTION_NOT_FOUND")
        return PortResult("SUCCEEDED", data={
            "execution_id": execution["execution_id"], "state": execution["state"], "reason": execution["reason"],
            "capability_id": execution["capability_id"], "capability_version": execution["capability_version"],
            "commitment_ref": None, "outcome_verification": execution["outcome_verification"]},
            trace={"handler_executed": False, "execution_id": execution["execution_id"],
                   "capability_ref": f"{execution['capability_id']}@{execution['capability_version']}"})


__all__ = ["DiscoveryService", "DiscoveryTurn", "FIXTURE_RESULT", "PortResult", "Refusal", "build_effect_intent"]
