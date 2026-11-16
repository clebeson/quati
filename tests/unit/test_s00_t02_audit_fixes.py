"""S00-T02 independent-audit regressions (P1-P3 findings and two coordinator decisions).

Each test discriminates one defect found by the audit:
P1 unguarded effect path (M30 rule 7 amendment), P2 capability-contract content binding,
P2 policy-registry file protection, P2 YAML/JSON nesting and event bounds, P3 raw
exceptions from refs/integers/surrogates, P3 cross-process CAS locking, and the
quati-json/1 decision that an integer-typed field never accepts a float.
"""

from __future__ import annotations

import copy
import fcntl
import json
import os
from datetime import timedelta
from pathlib import Path
import sys

import pytest
import yaml

from s00_t02_support import (
    ACTOR,
    NOW,
    REPOSITORY_ROOT,
    TENANT,
    CounterIds,
    base_decision_policy,
    base_machine,
    base_manifest,
    base_package,
    base_policy,
    write_package,
)
from quati.behavior.compiler import BehaviorCompiler, compile_documents
from quati.behavior.contracts import parse_json, parse_yaml
from quati.behavior.manifest import validate_manifest
from quati.behavior.store import BehaviorStore, PromotionApproval
from quati.behavior import trusted_config
from quati.behavior.trusted_config import load_decision_policy, load_policy, load_policy_registry, save_policy_registry
from quati.domain.canonical import digest
from quati.domain.diagnostics import ContractViolation, ErrorCode
from quati.domain.policy import (
    EffectIntent,
    PolicyContext,
    PolicyFileSnapshot,
    PolicyRegistry,
    adopt_policy,
    evaluate,
)
from quati.domain.statechart import next_state, validate_statechart_semantics

UID = os.getuid()
OWNER = PolicyContext(tenant_id=TENANT, actor_id=ACTOR, principal_kind="HUMAN", tenant_role="OWNER")


def _violation(function, *args, **kwargs) -> ContractViolation:
    with pytest.raises(ContractViolation) as caught:
        function(*args, **kwargs)
    return caught.value


def _edge(source, event, target, guard, action):
    return {"source": source, "event": event, "target": target, "guard": guard, "action": action}


def _short_machine(first_guard: str = "always", first_action: str = "record_progress") -> dict:
    return {
        "id": "short", "version": "1.0.0", "initial": "RECEIVED",
        "states": ["RECEIVED", "RESPOND", "CLOSED", "BLOCKED"], "terminal": ["CLOSED", "BLOCKED"],
        "budget": {"max_transitions": 10, "max_reinvestigations": 2},
        "transitions": [
            _edge("RECEIVED", "go", "RESPOND", first_guard, first_action),
            _edge("RESPOND", "done", "CLOSED", "always", "record_delivery"),
            _edge("RECEIVED", "fail", "BLOCKED", "always", "record_blocker"),
            _edge("RESPOND", "fail", "BLOCKED", "always", "record_blocker"),
        ],
    }


# ----------------------------------------------------------------------------- P1


def test_unguarded_path_to_delivery_is_forbidden() -> None:
    machine = _short_machine()
    error = _violation(validate_statechart_semantics, machine)
    assert error.rule_class == 7
    assert [(d.code, d.reason, d.path) for d in error.diagnostics] == [
        (ErrorCode.FORBIDDEN, "UNGUARDED_EFFECT_PATH", "transitions[1]")]
    # The trusted reducer refuses to run the machine at all, even with every guard true.
    with pytest.raises(ContractViolation):
        next_state(machine, "RECEIVED", "go", guard_results={"always": True}, transitions_used=0)
    assert _violation(compile_documents, base_package(), machine).reason == "UNGUARDED_EFFECT_PATH"
    # prepare_delivery straight from the initial state is the same bypass.
    skip = _short_machine(first_action="prepare_delivery")
    error = _violation(validate_statechart_semantics, skip)
    assert [(d.reason, d.path) for d in error.diagnostics] == [
        ("UNGUARDED_EFFECT_PATH", "transitions[0]"), ("UNGUARDED_EFFECT_PATH", "transitions[1]")]


def test_effect_path_guard_must_be_earlier_and_on_every_path() -> None:
    # An authorized_request (or safe_to_begin) edge earlier on the path satisfies the rule.
    for guard in ("authorized_request", "safe_to_begin"):
        assert validate_statechart_semantics(_short_machine(first_guard=guard)).state_count == 4
    # One guarded and one unguarded path into the same effect edge is still a bypass.
    mixed = _short_machine(first_guard="authorized_request")
    mixed["states"].insert(1, "SIDE")
    mixed["transitions"] += [_edge("RECEIVED", "side", "SIDE", "always", "record_progress"),
                             _edge("SIDE", "go", "RESPOND", "always", "record_progress"),
                             _edge("SIDE", "fail", "BLOCKED", "always", "record_blocker")]
    error = _violation(validate_statechart_semantics, mixed)
    assert [(d.reason, d.path) for d in error.diagnostics] == [("UNGUARDED_EFFECT_PATH", "transitions[1]")]
    # The effect edge's own safe_to_begin guard is not an *earlier* guard (commit_receipt).
    machine = {
        "id": "late", "version": "1.0.0", "initial": "WAIT",
        "states": ["WAIT", "CLASSIFIED", "REGISTER_WORK", "CLOSED", "BLOCKED"], "terminal": ["CLOSED", "BLOCKED"],
        "budget": {"max_transitions": 10, "max_reinvestigations": 1},
        "transitions": [
            _edge("WAIT", "resumed", "CLASSIFIED", "under_budget", "merge_context"),
            _edge("CLASSIFIED", "work", "REGISTER_WORK", "safe_to_begin", "commit_receipt"),
            _edge("REGISTER_WORK", "done", "CLOSED", "authorized_request", "record_progress"),
            _edge("WAIT", "fail", "BLOCKED", "always", "record_blocker"),
            _edge("CLASSIFIED", "fail", "BLOCKED", "always", "record_blocker"),
            _edge("REGISTER_WORK", "fail", "BLOCKED", "always", "record_blocker"),
        ],
    }
    error = _violation(validate_statechart_semantics, machine)
    assert [(d.reason, d.path) for d in error.diagnostics] == [("UNGUARDED_EFFECT_PATH", "transitions[1]")]


def test_shipped_statecharts_and_reference_compiler_agree_on_the_path_rule() -> None:
    for name in ("commitment.yaml", "interaction.yaml"):
        document = yaml.safe_load((REPOSITORY_ROOT / "examples" / "statecharts" / name).read_text("utf-8"))
        validate_statechart_semantics(document)
    sys.path.insert(0, str(REPOSITORY_ROOT / "spec_tools"))
    try:
        import behavior_compiler as reference
    finally:
        sys.path.pop(0)
    for machine in (_short_machine(), _short_machine(first_action="prepare_delivery")):
        with pytest.raises(ValueError, match="UNGUARDED_EFFECT_PATH"):
            reference.validate_machine(machine)
    reference.validate_machine(_short_machine(first_guard="authorized_request"))


# ----------------------------------------------------------------------------- P2 contracts


def test_capability_contract_content_is_bound_into_the_build_digest() -> None:
    package, machine = base_package(), base_machine()
    plain = compile_documents(package, machine)
    assert "capability_contracts" not in plain.config_bindings  # unchanged when no contract is given
    manifest = base_manifest()
    bound = compile_documents(package, machine, capability_contracts=[manifest])
    key = f"{manifest['id']}@{manifest['version']}"
    assert bound.config_bindings["capability_contracts"] == {key: digest(manifest)}
    changed = copy.deepcopy(manifest)
    changed["description"] = "A different description with the same id and version for this contract."
    validate_manifest(changed)
    other = compile_documents(package, machine, capability_contracts=[changed])
    assert other.text == bound.text and other.receipt == bound.receipt
    assert other.build_digest != bound.build_digest
    error = _violation(compile_documents, package, machine, capability_contracts=[manifest, copy.deepcopy(manifest)])
    assert (error.code, error.reason, error.path) == (
        ErrorCode.INVALID_INPUT, "DUPLICATE_CAPABILITY_CONTRACT", "capability_contracts[1]")


# ----------------------------------------------------------------------------- P2 registry


def _registry_file(path: Path, mode: int = 0o600) -> PolicyRegistry:
    snapshot = PolicyFileSnapshot(content=json.dumps(base_policy()).encode(), mode=0o600, owner_uid=UID)
    state = load_policy(snapshot, tenant_id=TENANT, installation_uid=UID, trusted_version=None)
    registry = adopt_policy(PolicyRegistry.empty(TENANT), state, expected_revision=0, actor=OWNER,
                            interactive=True, capability_context=False)
    save_policy_registry(path, registry, expected_revision=0)
    os.chmod(path, mode)
    return registry


def _write_policy(path: Path) -> None:
    path.write_text(json.dumps(base_policy()))
    os.chmod(path, 0o600)


def _decide(state):
    intent = EffectIntent(effect_id="eff-1", actor_id=ACTOR, tenant_id=TENANT, capability_id="research.fixture",
                          capability_version="1.0.0", binding_id="bind-1", binding_version="1", operation="invoke",
                          destination_ref="fixture:local", policy_version="0" * 64, idempotency_key="idem-1",
                          input_digest="1" * 64, effect_class="read", data_class="PUBLIC_SYNTHETIC",
                          integrity="TRUSTED", steering_args_user_confirmed=True, space_kind="PERSONAL")
    return evaluate(OWNER, intent, state, now=NOW, decision_id=CounterIds()(), runtime_profile="S02")


def test_policy_registry_file_has_the_policy_file_protections(tmp_path: Path) -> None:
    policy, registry_path = tmp_path / "policy.json", tmp_path / "registry.json"
    _write_policy(policy)
    _registry_file(registry_path)
    state = trusted_config.load_trusted_policy(policy, registry_path, tenant_id=TENANT, installation_uid=UID)
    assert state.available and _decide(state).verdict == "ALLOW"
    # A world-writable (forgeable) registry makes the policy unavailable: fail closed.
    os.chmod(registry_path, 0o666)
    error = _violation(load_policy_registry, registry_path, tenant_id=TENANT)
    assert (error.code, error.reason) == (ErrorCode.CONFIG_INVALID, "wrong_mode")
    state = trusted_config.load_trusted_policy(policy, registry_path, tenant_id=TENANT, installation_uid=UID)
    assert (state.available, state.cause) == (False, "registry_wrong_mode")
    assert (_decide(state).verdict, _decide(state).reason_code) == ("DENY", "policy_unavailable")
    os.chmod(registry_path, 0o600)
    error = _violation(load_policy_registry, registry_path, tenant_id=TENANT, installation_uid=UID + 1)
    assert error.reason == "wrong_owner"
    assert trusted_config.load_trusted_policy(policy, registry_path, tenant_id=TENANT,
                               installation_uid=UID + 1).cause == "registry_wrong_owner"
    # A symlinked registry is never followed.
    link = tmp_path / "link.json"
    link.symlink_to(registry_path)
    assert _violation(load_policy_registry, link, tenant_id=TENANT).reason == "not_regular_file"
    assert trusted_config.load_trusted_policy(policy, link, tenant_id=TENANT, installation_uid=UID).cause == \
        "registry_not_regular_file"
    # An absent registry is an empty one: nothing is trusted yet.
    state = trusted_config.load_trusted_policy(policy, tmp_path / "absent.json", tenant_id=TENANT, installation_uid=UID)
    assert (state.available, state.cause) == (False, "out_of_band_change")


# ----------------------------------------------------------------------------- P2 parser


def _nested_yaml(depth: int) -> bytes:
    """A mapping root (depth 1) holding ``depth - 1`` nested flow sequences."""
    return b"a: " + b"[" * (depth - 1) + b"]" * (depth - 1) + b"\n"


def test_yaml_nesting_depth_and_event_count_are_bounded() -> None:
    assert parse_yaml(_nested_yaml(64))["a"] is not None
    for depth in (65, 200_000):
        error = _violation(parse_yaml, _nested_yaml(depth))
        assert (error.code, error.reason, error.rule_class) == (ErrorCode.INVALID_INPUT, "PARSE_ERROR", 1)
    flat = b"a: [" + b"0," * 100_000 + b"0]\n"
    assert _violation(parse_yaml, flat).reason == "PARSE_ERROR"
    assert len(parse_yaml(b"a: [" + b"0," * 1000 + b"0]\n")["a"]) == 1001


def test_json_nesting_depth_is_bounded() -> None:
    assert parse_json(b'{"a": ' + b"[" * 63 + b"]" * 63 + b"}")["a"] is not None
    assert _violation(parse_json, b'{"a": ' + b"[" * 64 + b"]" * 64 + b"}").reason == "PARSE_ERROR"
    assert _violation(parse_json, b'{"a": ' + b"[" * 200_000 + b"]" * 200_000 + b"}").reason == "PARSE_ERROR"


# ----------------------------------------------------------------------------- P3 raw exceptions


@pytest.mark.parametrize("ref", ["./.", "./statechart.yaml", "a//statechart.yaml", "sub/./statechart.yaml",
                                 "statechart.yaml/"])
def test_dot_or_empty_ref_parts_are_rule_3(tmp_path: Path, ref: str) -> None:
    root = tmp_path / "pkg"
    package = base_package()
    package["statechart_ref"] = ref
    write_package(root, package)
    report = BehaviorCompiler(root).validate("package.yaml")
    assert (report.ok, report.rule_class) == (False, 3)
    assert [(d.code, d.reason, d.path) for d in report.diagnostics] == [
        (ErrorCode.INVALID_INPUT, "REF_INVALID", "statechart_ref")]


def test_oversized_integers_and_lone_surrogates_are_diagnostics(tmp_path: Path) -> None:
    error = _violation(parse_yaml, b"a: 1" + b"0" * 5000 + b"\n")
    assert (error.code, error.reason, error.rule_class) == (ErrorCode.INVALID_INPUT, "PARSE_ERROR", 1)
    assert _violation(parse_json, b'{"a": 1' + b"0" * 5000 + b"}").reason == "PARSE_ERROR"
    for raw in (b'a: "\\uD800"\n', b'"\\uD800": 1\n'):
        error = _violation(parse_yaml, raw)
        assert (error.code, error.reason, error.rule_class) == (ErrorCode.INVALID_INPUT, "INVALID_STRING", 1)
    assert _violation(parse_json, b'{"a": "\\ud800"}').reason == "INVALID_STRING"
    package = base_package()
    package["role"] = "assistant\ud800"
    error = _violation(compile_documents, package, base_machine())
    assert (error.reason, error.rule_class) == ("INVALID_STRING", 1)
    # Through the file entry the same inputs produce reports, never raw exceptions.
    root = tmp_path / "pkg"
    write_package(root)
    profile = root / "package.yaml"
    text = profile.read_text("utf-8")
    for bad in (text.replace("max_context_tokens: 6000", "max_context_tokens: 6" + "0" * 5000),
                text.replace("role: ", 'role: "\\uD800" #', 1)):
        assert bad != text
        profile.write_text(bad, "utf-8")
        report = BehaviorCompiler(root).validate("package.yaml")
        assert (report.ok, report.rule_class) == (False, 1)


# ----------------------------------------------------------------------------- P3 locking


def _lock_is_held(target: Path) -> bool:
    descriptor = os.open(f"{target}.lock", os.O_RDWR)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return True
    finally:
        os.close(descriptor)
    return False


def test_pointer_compare_and_swap_holds_a_sibling_file_lock(tmp_path: Path) -> None:
    observed = []
    pointer = tmp_path / "store" / "locks"  # lock files stay out of active/ (pointer files only)

    def hook(point: str) -> None:
        if point == "store.write_pointer.before_rename":
            observed.append(_lock_is_held(pointer / f"{package_id}.json"))

    store = BehaviorStore(tmp_path / "store", crash_hook=hook)
    root = tmp_path / "pkg"
    write_package(root)
    package_id = base_package()["id"]
    proposal = store.propose(root, "package.yaml", origin="OPERATOR", author="operator-1")
    report = store.validate(proposal.digest)
    approval = PromotionApproval(approval_id="apr-1", approver_id=ACTOR, approver_kind="HUMAN",
                                 artifact_digest=report.build_digest, expires_at=NOW + timedelta(minutes=5))
    store.promote(proposal.digest, approval=approval, expected_revision=0, now=NOW, verify_approval=lambda a: True)
    assert observed == [True]
    assert not _lock_is_held(pointer / f"{package_id}.json")  # released afterwards


def test_registry_compare_and_swap_holds_a_sibling_file_lock(tmp_path: Path) -> None:
    path = tmp_path / "registry.json"
    observed = []

    def hook(point: str) -> None:
        if point == "policy.write_registry.before_rename":
            observed.append(_lock_is_held(path))

    registry = _registry_file(path)
    save_policy_registry(path, registry, expected_revision=1, hook=hook)
    assert observed == [True] and not _lock_is_held(path)


# ----------------------------------------------------------------------------- integer floats


def test_integer_fields_reject_integer_valued_floats() -> None:
    package = base_package()
    package["execution"]["max_investigation_loops"] = float(package["execution"]["max_investigation_loops"])
    error = _violation(compile_documents, package, base_machine())
    assert (error.code, error.reason, error.path, error.rule_class) == (
        ErrorCode.INVALID_INPUT, "SCHEMA_INVALID", "execution.max_investigation_loops", 2)
    machine = base_machine()
    machine["budget"]["max_transitions"] = float(machine["budget"]["max_transitions"])
    assert _violation(compile_documents, base_package(), machine).path == "budget.max_transitions"
    document = base_decision_policy()
    channel = document["channel_policy"]
    name = next(key for key, value in channel.items() if type(value) is int)
    channel[name] = float(channel[name])
    error = _violation(load_decision_policy, json.dumps(document).encode())
    assert error.code is ErrorCode.CONFIG_INVALID


def test_in_memory_documents_get_the_parser_value_rules(tmp_path: Path) -> None:
    package = base_package()
    package["context"][7] = "x"
    assert _violation(compile_documents, package, base_machine()).reason == "NON_STRING_KEY"
    machine = base_machine()
    deep: dict = {}
    machine["budget"]["extra"] = deep
    for _ in range(70):
        deep["k"] = {}
        deep = deep["k"]
    error = _violation(compile_documents, base_package(), machine)
    assert (error.reason, error.rule_class) == ("PARSE_ERROR", 1)
    manifest = base_manifest()
    manifest["description"] = "bad\udfff"
    error = _violation(compile_documents, base_package(), base_machine(), capability_contracts=[manifest])
    assert error.reason == "INVALID_STRING"


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores file permission bits")
def test_unreadable_refs_are_rule_3_reports(tmp_path: Path) -> None:
    root = tmp_path / "pkg"
    package = base_package()
    package["statechart_ref"] = "sub/statechart.yaml"
    write_package(root, package)
    sub = root / "sub"
    sub.mkdir()
    target = sub / "statechart.yaml"
    target.write_text(yaml.safe_dump(base_machine()), "utf-8")
    try:
        target.chmod(0o000)
        report = BehaviorCompiler(root).validate("package.yaml")
        assert (report.rule_class, report.diagnostics[0].reason) == (3, "REF_UNREADABLE")
        target.chmod(0o600)
        sub.chmod(0o000)
        report = BehaviorCompiler(root).validate("package.yaml")
        assert (report.rule_class, report.diagnostics[0].reason) == (3, "REF_UNREADABLE")
    finally:
        sub.chmod(0o700)
        target.chmod(0o600)
