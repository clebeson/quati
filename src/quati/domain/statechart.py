"""Declarative statechart semantics (M30 rule classes 4-10) and the trusted reducer.

Pure domain code. The input is a statechart mapping that already passed
``contracts/statechart.schema.json`` (rule class 2, checked by ``quati.behavior``);
a minimal structural guard here keeps the reducer fail-closed for direct callers.

The v1 guard/action vocabulary and the protected-edge tables are ported exactly from
the offline reference compiler ``spec_tools/behavior_compiler.py``. Guard names are
data: the reducer never evaluates them, it only consumes results computed by
trusted code, and an edge fires only when its guard result is exactly ``True``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from quati.domain.canonical import digest
from quati.domain.diagnostics import ContractViolation, Diagnostic, ErrorCode

GUARD_REGISTRY = frozenset({
    "always", "authorized_request", "safe_to_begin", "under_budget", "valid_feedback",
    "under_reinvestigation_budget", "has_evidence", "delivery_acknowledged",
})
ACTION_REGISTRY = frozenset({
    "record_classification", "commit_receipt", "record_cancel", "start_work", "record_progress",
    "ask_user", "merge_context", "review_evidence", "deepen_work", "prepare_delivery",
    "prepare_partial_delivery", "record_blocker", "resume_work", "record_delivery",
})
# Actions that hand control to a human or stop the work (RFC-011 "escalation path").
ESCALATION_ACTIONS = frozenset({"record_cancel", "record_blocker", "ask_user"})

# action -> allowed (source, target, guard)
ACTION_EDGES = {
    "start_work": frozenset({("ACKNOWLEDGED", "IN_PROGRESS", "safe_to_begin")}),
    "resume_work": frozenset({("BLOCKED", "IN_PROGRESS", "safe_to_begin")}),
    "deepen_work": frozenset({("EVIDENCE_REVIEW", "IN_PROGRESS", "under_reinvestigation_budget")}),
    "review_evidence": frozenset({("IN_PROGRESS", "EVIDENCE_REVIEW", "under_budget")}),
}
# protected target -> allowed (source, guard, action)
PROTECTED_INCOMING = {
    "CLASSIFIED": frozenset({("RECEIVED", "authorized_request", "record_classification"),
                             ("INPUT_RECEIVED", "authorized_request", "record_classification"),
                             ("WAIT", "under_budget", "merge_context")}),
    "ACKNOWLEDGED": frozenset({("CLASSIFIED", "authorized_request", "commit_receipt")}),
    "IN_PROGRESS": frozenset({("ACKNOWLEDGED", "safe_to_begin", "start_work"),
                              ("IN_PROGRESS", "under_budget", "record_progress"),
                              ("WAITING_INPUT", "valid_feedback", "merge_context"),
                              ("EVIDENCE_REVIEW", "under_reinvestigation_budget", "deepen_work"),
                              ("BLOCKED", "safe_to_begin", "resume_work")}),
    "EVIDENCE_REVIEW": frozenset({("IN_PROGRESS", "under_budget", "review_evidence")}),
    "READY_TO_DELIVER": frozenset({("EVIDENCE_REVIEW", "has_evidence", "prepare_delivery"),
                                   ("EVIDENCE_REVIEW", "has_evidence", "prepare_partial_delivery")}),
    "DELIVERED": frozenset({("READY_TO_DELIVER", "delivery_acknowledged", "record_delivery")}),
    "REGISTER_WORK": frozenset({("CLASSIFIED", "safe_to_begin", "commit_receipt"),
                                ("ASK_CLARIFICATION", "safe_to_begin", "commit_receipt")}),
}
# protected action -> allowed (source, target, guard)
PROTECTED_ACTIONS = {
    "commit_receipt": frozenset({("CLASSIFIED", "ACKNOWLEDGED", "authorized_request"),
                                 ("CLASSIFIED", "REGISTER_WORK", "safe_to_begin"),
                                 ("ASK_CLARIFICATION", "REGISTER_WORK", "safe_to_begin")}),
    "record_delivery": frozenset({("READY_TO_DELIVER", "DELIVERED", "delivery_acknowledged"),
                                  ("RESPOND", "CLOSED", "always")}),
    "prepare_partial_delivery": frozenset({("EVIDENCE_REVIEW", "READY_TO_DELIVER", "has_evidence")}),
}
# Actions with durable or delivery effects: every path to them passes an authorizing edge first.
EFFECT_ACTIONS = frozenset({"commit_receipt", "start_work", "prepare_delivery", "record_delivery"})
AUTHORIZING_GUARDS = frozenset({"authorized_request", "safe_to_begin"})  # safe_to_begin implies authorization
CANCEL_STATE = "CANCELLED"
CANCEL_ACTION = "record_cancel"
TRANSITION_FIELDS = ("source", "event", "target", "guard", "action")


@dataclass(frozen=True)
class StatechartSummary:
    statechart_hash: str
    state_count: int
    transition_count: int


@dataclass(frozen=True)
class Step:
    accepted: bool
    state: str
    transition_index: int | None
    reason_code: str | None
    action: str | None = None


def _fail(rule_class: int, diagnostics: list[Diagnostic]) -> None:
    if diagnostics:
        raise ContractViolation(diagnostics, rule_class)


def _check_shape(machine: Any) -> None:
    """Fail closed on structures the schema would reject (direct domain callers)."""
    problems = []
    if not isinstance(machine, Mapping):
        problems.append("$")
    else:
        if not isinstance(machine.get("initial"), str):
            problems.append("initial")
        for key in ("states", "terminal", "transitions"):
            if not isinstance(machine.get(key), list):
                problems.append(key)
        budget = machine.get("budget")
        if not (isinstance(budget, Mapping) and all(
                type(budget.get(key)) is int for key in ("max_transitions", "max_reinvestigations"))):
            problems.append("budget")
        if not problems:
            for key in ("states", "terminal"):
                if not all(isinstance(item, str) for item in machine[key]):
                    problems.append(key)
            for index, transition in enumerate(machine["transitions"]):
                if not (isinstance(transition, Mapping)
                        and all(isinstance(transition.get(field), str) for field in TRANSITION_FIELDS)):
                    problems.append(f"transitions[{index}]")
    _fail(2, [Diagnostic(ErrorCode.INVALID_INPUT, path, "SCHEMA_INVALID", "statechart structure is invalid")
              for path in problems])


def _reach(start: str, edges: Mapping[str, list[str]]) -> set[str]:
    found = {start}
    queue = [start]
    while queue:
        for nxt in edges.get(queue.pop(), ()):
            if nxt not in found:
                found.add(nxt)
                queue.append(nxt)
    return found


def _protected_problem(transition: Mapping[str, str]) -> str | None:
    source, target, guard, action = (transition["source"], transition["target"], transition["guard"],
                                     transition["action"])
    if action in ACTION_EDGES and (source, target, guard) not in ACTION_EDGES[action]:
        return f"action {action} cannot bypass its required lifecycle stage"
    if target in PROTECTED_INCOMING and (source, guard, action) not in PROTECTED_INCOMING[target]:
        return f"protected state {target} entered outside its control semantics"
    if action in PROTECTED_ACTIONS and (source, target, guard) not in PROTECTED_ACTIONS[action]:
        return f"protected action {action} cannot be retargeted"
    if target == CANCEL_STATE and action != CANCEL_ACTION:
        return "cancellation requires record_cancel"
    return None


def _unauthorized_states(initial: str, transitions: list) -> set[str]:
    """States reachable from ``initial`` without traversing an authorizing edge."""
    edges: dict[str, list[str]] = {}
    for transition in transitions:
        if transition["guard"] not in AUTHORIZING_GUARDS:
            edges.setdefault(transition["source"], []).append(transition["target"])
    return _reach(initial, edges)


def validate_statechart_semantics(machine: Any) -> StatechartSummary:
    """Apply rule classes 4-10 in order; the first failing class raises with all its findings."""
    _check_shape(machine)
    states = list(machine["states"])
    state_set = set(states)
    terminal = set(machine["terminal"])
    initial = machine["initial"]
    transitions = machine["transitions"]

    # Rule 4: referenced states exist; the initial state is not terminal.
    missing: list[str] = []
    for name in [initial, *machine["terminal"]] + [t[f] for t in transitions for f in ("source", "target")]:
        if name not in state_set and name not in missing:
            missing.append(name)
    found = [Diagnostic(ErrorCode.INVALID_INPUT, f"states.{name}", "UNKNOWN_STATE",
                        f"state {name} is not declared") for name in missing]
    if initial in terminal:
        found.append(Diagnostic(ErrorCode.INVALID_INPUT, f"states.{initial}", "INITIAL_IS_TERMINAL",
                                "the initial state cannot be terminal"))
    _fail(4, found)

    # Rule 5: only registered guards and actions.
    found = []
    for index, transition in enumerate(transitions):
        if transition["guard"] not in GUARD_REGISTRY:
            found.append(Diagnostic(ErrorCode.UNSUPPORTED, f"transitions[{index}].guard", "UNREGISTERED_GUARD",
                                    f"guard {transition['guard']} is not registered"))
        if transition["action"] not in ACTION_REGISTRY:
            found.append(Diagnostic(ErrorCode.UNSUPPORTED, f"transitions[{index}].action", "UNREGISTERED_ACTION",
                                    f"action {transition['action']} is not registered"))
    _fail(5, found)

    # Rule 6: one transition per (source, event).
    found = []
    seen: set[tuple[str, str]] = set()
    for index, transition in enumerate(transitions):
        key = (transition["source"], transition["event"])
        if key in seen:
            found.append(Diagnostic(ErrorCode.INVALID_INPUT, f"transitions[{index}]", "AMBIGUOUS_TRANSITION",
                                    f"second transition for {key[0]}/{key[1]}"))
        seen.add(key)
    _fail(6, found)

    # Rule 7: protected edges keep their guards and lifecycle stages; effects need prior authorization.
    found = []
    for index, transition in enumerate(transitions):
        problem = _protected_problem(transition)
        if problem is not None:
            found.append(Diagnostic(ErrorCode.FORBIDDEN, f"transitions[{index}]", "PROTECTED_EDGE", problem))
    unauthorized = _unauthorized_states(initial, transitions)
    for index, transition in enumerate(transitions):
        if transition["action"] in EFFECT_ACTIONS and transition["source"] in unauthorized:
            found.append(Diagnostic(ErrorCode.FORBIDDEN, f"transitions[{index}]", "UNGUARDED_EFFECT_PATH",
                                    f"{transition['action']} is reachable without an earlier authorized_request"))
    _fail(7, found)

    # Rule 8: terminal states have no outgoing edge; every state is reachable and can finish.
    edges: dict[str, list[str]] = {}
    reverse: dict[str, list[str]] = {}
    for transition in transitions:
        edges.setdefault(transition["source"], []).append(transition["target"])
        reverse.setdefault(transition["target"], []).append(transition["source"])
    reachable = _reach(initial, edges)
    can_finish: set[str] = set()
    for name in terminal:
        can_finish |= _reach(name, reverse)
    found = []
    for name in states:
        if name in terminal and name in edges:
            found.append(Diagnostic(ErrorCode.INVALID_INPUT, f"states.{name}", "TERMINAL_HAS_OUTGOING",
                                    f"terminal state {name} has an outgoing transition"))
        if name not in reachable:
            found.append(Diagnostic(ErrorCode.INVALID_INPUT, f"states.{name}", "UNREACHABLE",
                                    f"state {name} is unreachable from {initial}"))
        if name not in can_finish:
            found.append(Diagnostic(ErrorCode.INVALID_INPUT, f"states.{name}", "DEAD_END",
                                    f"state {name} cannot reach a terminal state"))
    _fail(8, found)

    # Rule 9: every nonterminal state has a path to an escalation edge.
    escalating = {t["source"] for t in transitions if t["action"] in ESCALATION_ACTIONS}
    found = [Diagnostic(ErrorCode.INVALID_INPUT, f"states.{name}", "NO_ESCALATION_PATH",
                        f"state {name} has no path to cancel, block or ask the user")
             for name in states if name not in terminal and not (_reach(name, edges) & escalating)]
    _fail(9, found)

    # Rule 10: the transition budget can at least visit every state.
    if machine["budget"]["max_transitions"] < len(states):
        _fail(10, [Diagnostic(ErrorCode.BUDGET_EXCEEDED, "budget.max_transitions", "TRANSITION_BUDGET_TOO_SMALL",
                              "max_transitions is smaller than the number of states")])
    return StatechartSummary(digest(machine), len(states), len(transitions))


def next_state(machine: Any, state: str, event: str, *, guard_results: Mapping[str, Any],
               transitions_used: int) -> Step:
    """Trusted reducer: fire the unique (state, event) edge only when its guard result is True."""
    if type(transitions_used) is not int or transitions_used < 0:
        raise ValueError("transitions_used must be a non-negative integer")
    validate_statechart_semantics(machine)
    if state not in machine["states"]:
        return Step(False, state, None, "UNKNOWN_STATE")
    if state in machine["terminal"]:
        return Step(False, state, None, "TERMINAL_STATE")
    if transitions_used >= machine["budget"]["max_transitions"]:
        return Step(False, state, None, "BUDGET_EXCEEDED")
    for index, transition in enumerate(machine["transitions"]):
        if transition["source"] == state and transition["event"] == event:
            if guard_results.get(transition["guard"]) is True:
                return Step(True, transition["target"], index, None, transition["action"])
            return Step(False, state, None, "GUARD_DENIED")
    return Step(False, state, None, "NO_TRANSITION")
