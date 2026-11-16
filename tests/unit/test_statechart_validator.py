"""M30-FR-02 / M30-AT-02: statechart semantic rule classes 4-10 (CMP-02, CMP-03 legs)."""

from __future__ import annotations

import copy
from datetime import timedelta
from pathlib import Path

import pytest

from s00_t02_support import ACTOR, NOW, base_machine, base_package, mutate, write_package
from quati.behavior.compiler import BehaviorCompiler, compile_documents
from quati.behavior.store import BehaviorStore, PromotionApproval
from quati.domain.diagnostics import ContractViolation, ErrorCode
from quati.domain.statechart import (
    ACTION_REGISTRY,
    ESCALATION_ACTIONS,
    GUARD_REGISTRY,
    validate_statechart_semantics,
)


def _rejection(machine: dict) -> ContractViolation:
    with pytest.raises(ContractViolation) as caught:
        validate_statechart_semantics(machine)
    return caught.value


def _with_state(machine: dict, state: str, terminal: bool = False) -> dict:
    machine = copy.deepcopy(machine)
    machine["states"].append(state)
    if terminal:
        machine["terminal"].append(state)
    return machine


def _edge(source, event, target, guard="always", action="record_progress") -> dict:
    return {"source": source, "event": event, "target": target, "guard": guard, "action": action}


def rule_fixtures():
    """One malformed machine per rule row 4-10 with its expected (code, path, reason)."""
    m = base_machine
    cases = []
    cases.append(("4 initial missing", mutate(m(), "initial", "START"),
                  (ErrorCode.INVALID_INPUT, "states.START", "UNKNOWN_STATE")))
    unknown_terminal = m()
    unknown_terminal["terminal"].append("ARCHIVED")
    cases.append(("4 terminal missing", unknown_terminal,
                  (ErrorCode.INVALID_INPUT, "states.ARCHIVED", "UNKNOWN_STATE")))
    initial_terminal = m()
    initial_terminal["terminal"].append("RECEIVED")
    cases.append(("4 initial is terminal", initial_terminal,
                  (ErrorCode.INVALID_INPUT, "states.RECEIVED", "INITIAL_IS_TERMINAL")))
    unknown_target = m()
    unknown_target["transitions"][5]["target"] = "GHOST"
    cases.append(("4 unknown transition state", unknown_target,
                  (ErrorCode.INVALID_INPUT, "states.GHOST", "UNKNOWN_STATE")))
    unknown_guard = m()
    unknown_guard["transitions"][5]["guard"] = "skip_authorization"
    cases.append(("5 unregistered guard", unknown_guard,
                  (ErrorCode.UNSUPPORTED, "transitions[5].guard", "UNREGISTERED_GUARD")))
    unknown_action = m()
    unknown_action["transitions"][5]["action"] = "shell_exec"
    cases.append(("5 unregistered action", unknown_action,
                  (ErrorCode.UNSUPPORTED, "transitions[5].action", "UNREGISTERED_ACTION")))
    ambiguous = m()
    ambiguous["transitions"].append(_edge("IN_PROGRESS", "progress", "BLOCKED", action="record_blocker"))
    cases.append(("6 ambiguous", ambiguous,
                  (ErrorCode.INVALID_INPUT, "transitions[18]", "AMBIGUOUS_TRANSITION")))
    protected = m()
    protected["transitions"].append(_edge("RECEIVED", "skip", "DELIVERED", action="record_delivery"))
    cases.append(("7 protected", protected, (ErrorCode.FORBIDDEN, "transitions[18]", "PROTECTED_EDGE")))
    terminal_out = m()
    terminal_out["transitions"].append(_edge("CANCELLED", "reopen", "BLOCKED", action="record_blocker"))
    cases.append(("8 terminal outgoing", terminal_out,
                  (ErrorCode.INVALID_INPUT, "states.CANCELLED", "TERMINAL_HAS_OUTGOING")))
    orphan = _with_state(m(), "ORPHAN")
    orphan["transitions"].append(_edge("ORPHAN", "cancel", "CANCELLED", action="record_cancel"))
    cases.append(("8 unreachable", orphan, (ErrorCode.INVALID_INPUT, "states.ORPHAN", "UNREACHABLE")))
    limbo = _with_state(m(), "LIMBO")
    limbo["transitions"].append(_edge("IN_PROGRESS", "stall", "LIMBO"))
    cases.append(("8 dead end", limbo, (ErrorCode.INVALID_INPUT, "states.LIMBO", "DEAD_END")))
    no_escape = _with_state(_with_state(m(), "WRAP_UP"), "ARCHIVED", terminal=True)
    no_escape["transitions"].append(_edge("IN_PROGRESS", "wrap", "WRAP_UP", guard="under_budget"))
    no_escape["transitions"].append(_edge("WRAP_UP", "archive", "ARCHIVED"))
    cases.append(("9 no escalation path", no_escape,
                  (ErrorCode.INVALID_INPUT, "states.WRAP_UP", "NO_ESCALATION_PATH")))
    cases.append(("10 transition budget", mutate(m(), "budget.max_transitions", 9),
                  (ErrorCode.BUDGET_EXCEEDED, "budget.max_transitions", "TRANSITION_BUDGET_TOO_SMALL")))
    return cases


@pytest.mark.parametrize("label, machine, expected", rule_fixtures(), ids=lambda v: v if isinstance(v, str) else "")
def test_semantic_rule_classes_each_row(label: str, machine: dict, expected) -> None:
    error = _rejection(machine)
    assert (error.code, error.path, error.reason) == expected, label
    assert error.rule_class == int(label.split()[0])


def test_semantic_rule_classes() -> None:
    """M30-FR-02: each rule row 4-10 rejected with its code and path; the reference passes."""
    seen_classes = set()
    for label, machine, expected in rule_fixtures():
        error = _rejection(machine)
        assert (error.code, error.path, error.reason) == expected, label
        seen_classes.add(error.rule_class)
    assert seen_classes == {4, 5, 6, 7, 8, 9, 10}
    summary = validate_statechart_semantics(base_machine())
    assert (summary.state_count, summary.transition_count) == (10, 18)
    assert len(summary.statechart_hash) == 64
    # Behavior-level rule 10 checks (package budgets against the machine).
    error = pytest.raises(ContractViolation, compile_documents,
                          mutate(base_package(), "execution.max_investigation_loops", 3), base_machine()).value
    assert (error.code, error.path, error.rule_class) == (ErrorCode.BUDGET_EXCEEDED, "budget.max_reinvestigations", 10)
    error = pytest.raises(ContractViolation, compile_documents,
                          mutate(base_package(), "context.max_capability_candidates", 6), base_machine()).value
    assert (error.code, error.path, error.rule_class) == (
        ErrorCode.BUDGET_EXCEEDED, "context.max_capability_candidates", 10)
    compile_documents(mutate(base_package(), "context.max_capability_candidates", 5), base_machine())


def test_first_failing_rule_class_wins_and_reports_all_its_diagnostics() -> None:
    machine = base_machine()
    machine["transitions"][5]["guard"] = "skip_authorization"     # rule 5
    machine["transitions"][6]["action"] = "shell_exec"            # rule 5
    machine["transitions"].append(_edge("CANCELLED", "x", "BLOCKED", action="record_blocker"))  # rule 8
    error = _rejection(machine)
    assert error.rule_class == 5
    assert [d.path for d in error.diagnostics] == ["transitions[5].guard", "transitions[6].action"]


def test_registries_are_closed_and_cover_reference_vocabulary() -> None:
    machine = base_machine()
    assert {t["guard"] for t in machine["transitions"]} <= GUARD_REGISTRY
    assert {t["action"] for t in machine["transitions"]} <= ACTION_REGISTRY
    assert ESCALATION_ACTIONS == frozenset({"record_cancel", "record_blocker", "ask_user"})
    assert isinstance(GUARD_REGISTRY, frozenset) and isinstance(ACTION_REGISTRY, frozenset)
    for name in ("allow_anything", "skip_authorization", "eval", "shell_exec"):
        assert name not in GUARD_REGISTRY | ACTION_REGISTRY


def _approval(build_digest: str) -> PromotionApproval:
    return PromotionApproval(approval_id="apr-0001", approver_id=ACTOR, approver_kind="HUMAN",
                             artifact_digest=build_digest, expires_at=NOW + timedelta(minutes=5))


def test_malformed_machines_rejected(tmp_path: Path) -> None:
    """M30-AT-02: dead-end, unregistered skip_authorization guard, unbudgeted cycle."""
    store = BehaviorStore(tmp_path / "store")
    good_root = tmp_path / "good"
    write_package(good_root)
    good = store.propose(good_root, "package.yaml", origin="OPERATOR", author="operator-1")
    report = store.validate(good.digest)
    store.promote(good.digest, approval=_approval(report.build_digest), expected_revision=0, now=NOW,
                  verify_approval=lambda approval: True)
    active_before = store.active("executive-secretary")

    dead_end = _with_state(base_machine(), "X")
    dead_end["transitions"].append(_edge("IN_PROGRESS", "park", "X"))
    skip_guard = base_machine()
    skip_guard["transitions"][1]["guard"] = "skip_authorization"
    unbudgeted = base_machine()
    del unbudgeted["budget"]["max_transitions"]
    expected = [
        (dead_end, "states.X", ErrorCode.INVALID_INPUT),
        (skip_guard, "transitions[1].guard", ErrorCode.UNSUPPORTED),
        (unbudgeted, "budget.max_transitions", ErrorCode.INVALID_INPUT),
    ]
    for index, (machine, path, code) in enumerate(expected):
        root = tmp_path / f"bad-{index}"
        write_package(root, base_package(), machine)
        compiled = BehaviorCompiler(root).validate("package.yaml")
        assert compiled.ok is False
        assert [d.path for d in compiled.diagnostics] == [path]
        assert compiled.diagnostics[0].code is code
        rejected = store.validate(store.propose(root, "package.yaml", origin="MODEL", author="agent").digest)
        assert rejected.ok is False and rejected.diagnostics[0].path == path
        assert store.active("executive-secretary") == active_before
