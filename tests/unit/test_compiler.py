"""M30 behavior compiler: CMP-01, CMP-02, CMP-03 and the M30 FR/AT oracle rows.

Contract entry: ``quati.behavior.compiler`` and the S00 local file store
``quati.behavior.store``. The ``quati behavior ...`` CLI is not wired by S00-T02
(the CLI package is owned by another task); these tests use the public library entry.
"""

from __future__ import annotations

import json
import os
from datetime import timedelta
from pathlib import Path
import subprocess
import sys

import jsonschema
import pytest
import yaml

from s00_t02_support import (
    ACTOR,
    CONTRACTS,
    EXAMPLES,
    NOW,
    REPOSITORY_ROOT,
    base_machine,
    base_package,
    mutate,
    write_package,
)
from quati.behavior.compiler import (
    COMPILER_VERSION,
    PROMPT_SECTIONS,
    BehaviorCompiler,
    compile_documents,
    diff_documents,
)
from quati.behavior.store import BehaviorStore, PromotionApproval
from quati.domain.canonical import CANONICAL_RULE, canonical_bytes, digest
from quati.domain.diagnostics import ContractViolation, ErrorCode

RECEIPT_SCHEMA = json.loads((CONTRACTS / "prompt-build-receipt.schema.json").read_text())
NO_RIGHTS = "This prompt does not grant rights; all actions pass trusted code authorization."


class SimulatedCrash(Exception):
    pass


class CrashAt:
    """Named crash-injection hook: raises once at the named point."""

    def __init__(self, point: str | None) -> None:
        self.point = point
        self.seen: list[str] = []

    def __call__(self, name: str) -> None:
        self.seen.append(name)
        if name == self.point:
            self.point = None
            raise SimulatedCrash(name)


class TrustedApprovals:
    """Stands in for the trusted approval store (ApprovalPort arrives in S02)."""

    def __init__(self, *approval_ids: str) -> None:
        self.known = set(approval_ids)
        self.calls = 0

    def __call__(self, approval: PromotionApproval) -> bool:
        self.calls += 1
        return approval.approval_id in self.known


def approval_for(build_digest: str, approval_id: str = "apr-0001", **overrides) -> PromotionApproval:
    fields = dict(approval_id=approval_id, approver_id=ACTOR, approver_kind="HUMAN",
                  artifact_digest=build_digest, expires_at=NOW + timedelta(minutes=15))
    fields.update(overrides)
    return PromotionApproval(**fields)


def concise_config() -> dict:
    """FX-CONFIG-A: frozen profile "concise" with a fixed locale."""
    package = base_package()
    package["id"] = "concise"
    package["interaction"]["verbosity"] = "brief"
    package["interaction"]["language_policy"] = "explicit_override"
    package["interaction"]["language_override"] = "pt-BR"
    return package


COMPILE_SCRIPT = """
import json, sys
from pathlib import Path
from quati.behavior.compiler import BehaviorCompiler
artifact = BehaviorCompiler(Path(sys.argv[1])).compile('package.yaml')
sys.stdout.write(json.dumps({'receipt': artifact.receipt, 'build_digest': artifact.build_digest},
                            sort_keys=True))
"""


def _compile_in_clean_process(root: Path) -> bytes:
    env = {"PATH": "/usr/bin:/bin", "PYTHONPATH": str(REPOSITORY_ROOT / "src"), "PYTHONHASHSEED": "0",
           "HOME": str(root)}
    # sys.executable is already absolute; resolving the venv symlink would leave the venv.
    completed = subprocess.run([sys.executable, "-c", COMPILE_SCRIPT, str(root)],
                               cwd=root, env=env, capture_output=True, check=True)
    return completed.stdout


# --------------------------------------------------------------------------- CMP-01


def test_cmp_01(tmp_path: Path) -> None:
    root = tmp_path / "config-a"
    write_package(root, concise_config())
    first = _compile_in_clean_process(root)
    second = _compile_in_clean_process(root)
    assert first == second  # byte-identical receipts from two clean processes
    receipt = json.loads(first)["receipt"]
    jsonschema.validate(receipt, RECEIPT_SCHEMA)
    assert receipt["compiler_version"] == COMPILER_VERSION
    assert receipt["source_versions"] == {"behavior": "1.0.0", "statechart": "1.0.0"}
    assert receipt["behavior_id"] == "concise"
    assert CANONICAL_RULE == "quati-json/1"
    assert receipt["behavior_hash"] == digest(concise_config())

    # Negative: change one profile field; digest changes and the diff names the input.
    changed = mutate(concise_config(), "interaction.verbosity", "detailed")
    changed_root = tmp_path / "config-b"
    write_package(changed_root, changed)
    changed_receipt = json.loads(_compile_in_clean_process(changed_root))["receipt"]
    assert changed_receipt["prompt_hash"] != receipt["prompt_hash"]
    assert changed_receipt["behavior_hash"] != receipt["behavior_hash"]
    assert diff_documents(concise_config(), changed) == ("interaction.verbosity",)

    # Fault: interruption before the receipt write leaves no partial receipt; retry is identical.
    crash = CrashAt("store.write_object.before_rename")
    store = BehaviorStore(tmp_path / "store", crash_hook=crash)
    proposal = store.propose(root, "package.yaml", origin="OPERATOR", author="operator-1")
    with pytest.raises(SimulatedCrash):
        store.validate(proposal.digest)
    objects = tmp_path / "store" / "objects"
    assert sorted(path.name for path in objects.iterdir() if path.name.endswith(".json")) == sorted(
        [proposal.package_object, proposal.statechart_object])
    assert store.proposal_state(proposal.digest) == "PROPOSED"
    report = BehaviorStore(tmp_path / "store").validate(proposal.digest)
    assert report.ok and report.build_digest == json.loads(first)["build_digest"]
    assert not [path for path in objects.iterdir() if path.name.startswith(".tmp")]


def test_compile_receipt_deterministic(tmp_path: Path) -> None:
    """M30-FR-01 with the examples executive-secretary package."""
    compiler = BehaviorCompiler(REPOSITORY_ROOT)
    first = compiler.compile("examples/behavior/executive-secretary.yaml")
    second = compiler.compile("examples/behavior/executive-secretary.yaml")
    jsonschema.validate(first.receipt, RECEIPT_SCHEMA)
    assert first.receipt == second.receipt and first.text == second.text
    assert first.receipt["sections"] == list(PROMPT_SECTIONS)
    assert PROMPT_SECTIONS == ("kernel_invariants", "role", "interaction", "execution", "language")
    assert first.text.splitlines()[0].startswith("Protected Quati invariants:")
    assert first.text.splitlines()[-1] == NO_RIGHTS
    assert first.receipt["prompt_hash"] == digest_text(first.text)
    assert first.receipt["policy_ref"] == "trusted_policy/default@" + first.receipt["policy_hash"]

    # Cross-check: the offline reference compiler output for the same inputs.
    reference = json.loads((EXAMPLES / "behavior" / "compiled_receipt.reference.json").read_text())
    for field in ("behavior_hash", "statechart_hash", "prompt_hash", "policy_hash", "policy_ref",
                  "effective_limits", "sections", "token_budget", "model_profile_ref", "source_versions"):
        assert first.receipt[field] == reference[field], field
    preview = (EXAMPLES / "behavior" / "prompt_preview.reference.txt").read_text().split("\n\n", 1)[1]
    assert first.text == preview.rstrip("\n")

    # Reordered YAML keys give the same digest.
    package = yaml.safe_load((EXAMPLES / "behavior" / "executive-secretary.yaml").read_text())
    machine = yaml.safe_load((EXAMPLES / "statecharts" / "commitment.yaml").read_text())
    reordered = dict(reversed(list(package.items())))
    reordered["interaction"] = dict(reversed(list(package["interaction"].items())))
    root = tmp_path / "reordered"
    root.mkdir()
    reordered["statechart_ref"] = "chart.yaml"
    (root / "p.yaml").write_text(yaml.safe_dump(reordered, sort_keys=False))
    (root / "chart.yaml").write_text(yaml.safe_dump(dict(reversed(list(machine.items()))), sort_keys=False))
    third = BehaviorCompiler(root).compile("p.yaml")
    assert third.receipt["statechart_hash"] == first.receipt["statechart_hash"]
    assert third.receipt["prompt_hash"] == first.receipt["prompt_hash"]

    # A changed language section changes only prompt_hash among the output digests.
    language = mutate(package, "interaction.language_policy", "explicit_override")
    language["interaction"]["language_override"] = "es"
    fourth = compile_documents(language, machine)
    assert fourth.receipt["prompt_hash"] != first.receipt["prompt_hash"]
    for field in ("statechart_hash", "policy_hash", "policy_ref", "effective_limits", "token_budget",
                  "model_profile_ref", "compiler_version", "sections"):
        assert fourth.receipt[field] == first.receipt[field], field
    assert "Reply in language tag es" in fourth.text


def digest_text(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_lifecycle_commands_and_safe_parsing(tmp_path: Path) -> None:
    """M30-FR-03 with FX-M30-BOUNDARY."""
    store = BehaviorStore(tmp_path / "store")
    duplicate = tmp_path / "dup"
    duplicate.mkdir()
    (duplicate / "package.yaml").write_text(
        yaml.safe_dump(base_package(), sort_keys=False) + "role: second role text that wins silently\n")
    error = pytest.raises(ContractViolation, store.propose, duplicate, "package.yaml",
                          origin="OPERATOR", author="operator-1").value
    assert (error.code, error.reason) == (ErrorCode.INVALID_INPUT, "DUPLICATE_KEY")
    tagged = tmp_path / "tag"
    tagged.mkdir()
    (tagged / "package.yaml").write_text("id: !!python/object:os.system {}\n")
    error = pytest.raises(ContractViolation, store.propose, tagged, "package.yaml",
                          origin="OPERATOR", author="operator-1").value
    assert (error.code, error.reason) == (ErrorCode.INVALID_INPUT, "TAG_FORBIDDEN")

    p1_root = tmp_path / "p1"
    write_package(p1_root)
    p1 = store.propose(p1_root, "package.yaml", origin="OPERATOR", author="operator-1")
    assert store.proposal_state(p1.digest) == "PROPOSED"
    # Promotion before validation is refused.
    error = pytest.raises(ContractViolation, store.promote, p1.digest, approval=approval_for("0" * 64),
                          expected_revision=0, now=NOW, verify_approval=TrustedApprovals("apr-0001")).value
    assert (error.code, error.reason) == (ErrorCode.FORBIDDEN, "VALIDATION_REQUIRED")
    report = store.validate(p1.digest)
    assert report.ok and store.proposal_state(p1.digest) == "VALIDATED"
    # Promote without approval is refused with APPROVAL_REQUIRED and changes nothing.
    error = pytest.raises(ContractViolation, store.promote, p1.digest, approval=None, expected_revision=0,
                          now=NOW, verify_approval=TrustedApprovals()).value
    assert (error.code, error.reason) == (ErrorCode.APPROVAL_REQUIRED, "approval_missing")
    assert store.active("executive-secretary") .active_digest is None

    # render returns the exact stored prompt artifact.
    rendered = store.render(report.build_digest)
    assert rendered.receipt == report.receipt and rendered.build_digest == report.build_digest
    error = pytest.raises(ContractViolation, store.render, "f" * 64).value
    assert error.code is ErrorCode.NOT_FOUND

    # simulate runs the trusted reducer on a stored proposal.
    trace = store.simulate(p1.digest, [
        ("classified", {"authorized_request": True}),
        ("accepted", {"authorized_request": True}),
        ("start", {"safe_to_begin": False}),
        ("cancel", {"always": True}),
    ])
    assert [step.state for step in trace] == ["CLASSIFIED", "ACKNOWLEDGED", "ACKNOWLEDGED", "CANCELLED"]
    assert [step.accepted for step in trace] == [True, True, False, True]

    trusted = TrustedApprovals("apr-0001", "apr-0002")
    pointer = store.promote(p1.digest, approval=approval_for(report.build_digest), expected_revision=0,
                            now=NOW, verify_approval=trusted)
    assert (pointer.active_digest, pointer.revision) == (report.build_digest, 1)
    assert store.proposal_state(p1.digest) == "ACTIVE"

    # Rollback to a digest that was never active is NOT_FOUND.
    error = pytest.raises(ContractViolation, store.rollback, "executive-secretary", "a" * 64,
                          expected_revision=1).value
    assert (error.code, error.reason) == (ErrorCode.NOT_FOUND, "NEVER_ACTIVE")
    error = pytest.raises(ContractViolation, store.rollback, "executive-secretary", report.build_digest,
                          expected_revision=1).value
    assert (error.code, error.reason) == (ErrorCode.NOT_FOUND, "NEVER_ACTIVE")

    # A crash injected mid-promote leaves exactly the old or the new pointer.
    p2_root = tmp_path / "p2"
    write_package(p2_root, mutate(base_package(), "interaction.clarification_style", "only_blocking"))
    p2 = store.propose(p2_root, "package.yaml", origin="OPERATOR", author="operator-1")
    report2 = store.validate(p2.digest)
    for point, expected in (("store.write_pointer.before_rename", report.build_digest),
                            ("store.write_pointer.after_rename", report2.build_digest)):
        crashing = BehaviorStore(tmp_path / "store", crash_hook=CrashAt(point))
        current = crashing.active("executive-secretary")
        with pytest.raises(SimulatedCrash):
            crashing.promote(p2.digest, approval=approval_for(report2.build_digest, "apr-0002"),
                             expected_revision=current.revision, now=NOW, verify_approval=trusted)
        after = BehaviorStore(tmp_path / "store").active("executive-secretary")
        assert after.active_digest == expected, point
        assert after.active_digest in {report.build_digest, report2.build_digest}
        pointer_files = list((tmp_path / "store" / "active").iterdir())
        assert [path.name for path in pointer_files] == ["executive-secretary.json"]


def test_profile_change_and_rollback_digests(tmp_path: Path) -> None:
    """M30-AT-01 / CMP-04 leg: P1 and P2 differ only in clarification style."""
    store = BehaviorStore(tmp_path / "store")
    p1_root, p2_root = tmp_path / "p1", tmp_path / "p2"
    write_package(p1_root)
    write_package(p2_root, mutate(base_package(), "interaction.clarification_style", "only_blocking"))
    p1 = store.propose(p1_root, "package.yaml", origin="OPERATOR", author="operator-1")
    p2 = store.propose(p2_root, "package.yaml", origin="OPERATOR", author="operator-1")
    r1, r2 = store.validate(p1.digest), store.validate(p2.digest)
    assert r1.receipt["prompt_hash"] != r2.receipt["prompt_hash"]
    assert r1.receipt["statechart_hash"] == r2.receipt["statechart_hash"]
    assert store.validate(p1.digest).build_digest == r1.build_digest  # recompiling P1
    assert store.diff(p1.digest, p2.digest) == ("package.interaction.clarification_style",)

    trusted = TrustedApprovals("apr-1", "apr-2", "apr-3")
    store.promote(p1.digest, approval=approval_for(r1.build_digest, "apr-1"), expected_revision=0, now=NOW,
                  verify_approval=trusted)
    # Stale expected revision is a conflict and changes nothing.
    error = pytest.raises(ContractViolation, store.promote, p2.digest,
                          approval=approval_for(r2.build_digest, "apr-2"), expected_revision=0, now=NOW,
                          verify_approval=trusted).value
    assert (error.code, error.reason) == (ErrorCode.REVISION_CONFLICT, "REVISION_CONFLICT")
    assert store.active("executive-secretary").active_digest == r1.build_digest
    pointer = store.promote(p2.digest, approval=approval_for(r2.build_digest, "apr-2"), expected_revision=1,
                            now=NOW, verify_approval=trusted)
    assert pointer.active_digest == r2.build_digest and pointer.history == (r1.build_digest,)
    assert store.proposal_state(p1.digest) == "SUPERSEDED"
    error = pytest.raises(ContractViolation, store.rollback, "executive-secretary", r1.build_digest,
                          expected_revision=1).value
    assert error.code is ErrorCode.REVISION_CONFLICT
    pointer = store.rollback("executive-secretary", r1.build_digest, expected_revision=2)
    assert (pointer.active_digest, pointer.revision) == (r1.build_digest, 3)
    assert BehaviorStore(tmp_path / "store").active("executive-secretary").active_digest == r1.build_digest
    assert store.render(pointer.active_digest).receipt == r1.receipt


# --------------------------------------------------------------------------- CMP-02


def test_cmp_02(tmp_path: Path) -> None:
    """FX-UNSAFE-CONFIG: guard allow_anything and action shell_exec."""
    store = BehaviorStore(tmp_path / "store")
    base_root = tmp_path / "baseline"
    write_package(base_root)
    baseline = store.propose(base_root, "package.yaml", origin="OPERATOR", author="operator-1")
    baseline_report = store.validate(baseline.digest)
    store.promote(baseline.digest, approval=approval_for(baseline_report.build_digest), expected_revision=0,
                  now=NOW, verify_approval=TrustedApprovals("apr-0001"))
    before = store.active("executive-secretary")
    permissions_before = store.render(before.active_digest).receipt["effective_limits"]

    machine = base_machine()
    machine["transitions"][5]["guard"] = "allow_anything"
    machine["transitions"][6]["action"] = "shell_exec"
    unsafe_root = tmp_path / "unsafe"
    write_package(unsafe_root, base_package(), machine)
    candidate = store.propose(unsafe_root, "package.yaml", origin="MODEL", author="agent-7")
    report = store.validate(candidate.digest)
    assert report.ok is False and report.rule_class == 5 and report.build_digest is None
    assert [(d.code, d.path, d.reason) for d in report.diagnostics] == [
        (ErrorCode.UNSUPPORTED, "transitions[5].guard", "UNREGISTERED_GUARD"),
        (ErrorCode.UNSUPPORTED, "transitions[6].action", "UNREGISTERED_ACTION"),
    ]
    assert store.proposal_state(candidate.digest) == "REJECTED"
    error = pytest.raises(ContractViolation, store.promote, candidate.digest,
                          approval=approval_for("0" * 64), expected_revision=before.revision, now=NOW,
                          verify_approval=TrustedApprovals("apr-0001")).value
    assert (error.code, error.reason) == (ErrorCode.FORBIDDEN, "PROPOSAL_REJECTED")
    assert json.loads(report.to_json())["diagnostics"][0]["path"] == "transitions[5].guard"

    # Negative: alias and nested-expression encodings are rejected semantically or at parse.
    alias_root = tmp_path / "alias"
    alias_root.mkdir()
    (alias_root / "package.yaml").write_text(yaml.safe_dump(base_package(), sort_keys=False))
    chart = yaml.safe_dump(base_machine(), sort_keys=False)
    (alias_root / "statechart.yaml").write_text("x-unsafe: &unsafe shell_exec\n" + chart.replace(
        "action: record_progress", "action: *unsafe", 1))
    alias = store.propose(alias_root, "package.yaml", origin="MODEL", author="agent-7")
    alias_report = store.validate(alias.digest)
    assert alias_report.ok is False and alias_report.rule_class == 1
    assert alias_report.diagnostics[0].reason == "ALIAS_FORBIDDEN"
    for encoded in ("{{ 'shell' ~ '_exec' }}", {"call": "shell_exec"}, ["shell_exec"]):
        nested = base_machine()
        nested["transitions"][6]["action"] = encoded
        nested_root = tmp_path / f"nested-{type(encoded).__name__}"
        write_package(nested_root, base_package(), nested)
        nested_report = store.validate(store.propose(nested_root, "package.yaml", origin="MODEL",
                                                     author="agent-7").digest)
        assert nested_report.ok is False and nested_report.rule_class == 2
        assert nested_report.diagnostics[0].path == "transitions[6].action"

    # Fault: malformed/truncated candidate input fails validation and keeps the active digest.
    truncated_root = tmp_path / "truncated"
    write_package(truncated_root)
    text = (truncated_root / "statechart.yaml").read_text()
    (truncated_root / "statechart.yaml").write_text(text[: len(text) // 2] + "\n  - {source: [")
    truncated = store.propose(truncated_root, "package.yaml", origin="OPERATOR", author="operator-1")
    truncated_report = store.validate(truncated.digest)
    assert truncated_report.ok is False and truncated_report.rule_class == 1
    after = store.active("executive-secretary")
    assert after == before
    assert store.render(after.active_digest).receipt["effective_limits"] == permissions_before


# --------------------------------------------------------------------------- CMP-03


def dead_end_chart() -> dict:
    """FX-DEAD-END-CHART: START->WORK, isolated ORPHAN, no terminal edge from WORK."""
    return {
        "id": "dead-end", "version": "1.0.0", "initial": "START",
        "states": ["START", "WORK", "ORPHAN", "DONE"], "terminal": ["DONE"],
        "budget": {"max_transitions": 10, "max_reinvestigations": 2},
        "transitions": [
            {"source": "START", "event": "begin", "target": "WORK", "guard": "always",
             "action": "record_progress"},
            {"source": "ORPHAN", "event": "finish", "target": "DONE", "guard": "always",
             "action": "record_cancel"},
        ],
    }


def test_cmp_03(tmp_path: Path) -> None:
    store = BehaviorStore(tmp_path / "store")
    good_root = tmp_path / "good"
    write_package(good_root)
    good = store.propose(good_root, "package.yaml", origin="OPERATOR", author="operator-1")
    good_report = store.validate(good.digest)
    store.promote(good.digest, approval=approval_for(good_report.build_digest), expected_revision=0, now=NOW,
                  verify_approval=TrustedApprovals("apr-0001"))
    before = store.active("executive-secretary")

    root = tmp_path / "dead-end"
    write_package(root, base_package(), dead_end_chart())
    proposal = store.propose(root, "package.yaml", origin="OPERATOR", author="operator-1")
    report = store.validate(proposal.digest)
    assert report.ok is False and report.rule_class == 8 and report.build_digest is None
    found = {(d.path, d.reason) for d in report.diagnostics}
    assert ("states.ORPHAN", "UNREACHABLE") in found
    assert ("states.WORK", "DEAD_END") in found
    assert all(d.code is ErrorCode.INVALID_INPUT for d in report.diagnostics)
    # No prompt/statechart receipt is stored or promotable for the rejected chart.
    assert store.proposal_state(proposal.digest) == "REJECTED"
    assert store.active("executive-secretary") == before

    # Negative: an edge into ORPHAN still leaves WORK without a terminal path.
    chart = dead_end_chart()
    chart["transitions"].append({"source": "START", "event": "detour", "target": "ORPHAN", "guard": "always",
                                 "action": "record_progress"})
    root2 = tmp_path / "dead-end-2"
    write_package(root2, base_package(), chart)
    report2 = store.validate(store.propose(root2, "package.yaml", origin="OPERATOR", author="o").digest)
    assert report2.ok is False and report2.rule_class == 8
    assert {(d.path, d.reason) for d in report2.diagnostics} == {("states.WORK", "DEAD_END")}

    # Fault: a crash during validation leaves the active chart version unchanged.
    crashing = BehaviorStore(tmp_path / "store", crash_hook=CrashAt("store.validate.before_report"))
    with pytest.raises(SimulatedCrash):
        crashing.validate(proposal.digest)
    assert BehaviorStore(tmp_path / "store").active("executive-secretary") == before


def test_store_rejects_unknown_and_foreign_inputs(tmp_path: Path) -> None:
    store = BehaviorStore(tmp_path / "store")
    for operation in (store.validate, store.proposal_state):
        error = pytest.raises(ContractViolation, operation, "e" * 64).value
        assert (error.code, error.reason) == (ErrorCode.NOT_FOUND, "UNKNOWN_PROPOSAL")
    error = pytest.raises(ContractViolation, store.diff, "e" * 64, "d" * 64).value
    assert error.code is ErrorCode.NOT_FOUND
    error = pytest.raises(ContractViolation, store.simulate, "e" * 64, []).value
    assert error.code is ErrorCode.NOT_FOUND
    for bad in ("../../etc/passwd", "ABC", "a" * 63):
        error = pytest.raises(ContractViolation, store.render, bad).value
        assert (error.code, error.reason) == (ErrorCode.INVALID_INPUT, "DIGEST_INVALID")
    with pytest.raises(ContractViolation) as caught:
        store.propose(tmp_path, "package.yaml", origin="ROOT", author="x")
    assert caught.value.reason == "ORIGIN_INVALID"
    root = tmp_path / "pkg"
    write_package(root)
    with pytest.raises(ContractViolation) as caught:
        store.propose(root, "package.yaml", origin="OPERATOR", author="")
    assert caught.value.reason == "AUTHOR_MISSING"
    assert store.active("unknown-behavior").revision == 0
    error = pytest.raises(ContractViolation, store.active, "../evil").value
    assert error.reason == "BEHAVIOR_ID_INVALID"


def test_store_detects_tampered_objects(tmp_path: Path) -> None:
    store = BehaviorStore(tmp_path / "store")
    root = tmp_path / "pkg"
    write_package(root)
    proposal = store.propose(root, "package.yaml", origin="OPERATOR", author="operator-1")
    report = store.validate(proposal.digest)
    artifact_path = tmp_path / "store" / "objects" / f"{report.build_digest}.json"
    document = json.loads(artifact_path.read_text())
    document["text"] = document["text"].replace("brief", "detailed")
    artifact_path.write_text(json.dumps(document))
    error = pytest.raises(ContractViolation, store.render, report.build_digest).value
    assert (error.code, error.reason) == (ErrorCode.INTERNAL_ERROR, "DIGEST_MISMATCH")


def test_store_proposal_is_idempotent_and_content_addressed(tmp_path: Path) -> None:
    store = BehaviorStore(tmp_path / "store")
    root = tmp_path / "pkg"
    write_package(root)
    first = store.propose(root, "package.yaml", origin="OPERATOR", author="operator-1")
    second = store.propose(root, "package.yaml", origin="OPERATOR", author="operator-1")
    assert first == second
    model = store.propose(root, "package.yaml", origin="MODEL", author="agent-1")
    assert model.digest != first.digest and model.origin == "MODEL"
    record = json.loads((tmp_path / "store" / "proposals" / f"{model.digest}.json").read_text())
    assert record["origin"] == "MODEL" and record["author"] == "agent-1"
    assert canonical_bytes(record) == (tmp_path / "store" / "proposals" / f"{model.digest}.json").read_bytes()
    assert os.stat(tmp_path / "store" / "proposals" / f"{model.digest}.json").st_size > 0
