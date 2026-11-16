"""S00-T02 local assertions A01-A03 (M14, M30 contribution; K9/K10 boundaries).

A01: malformed nested schemas, duplicate YAML keys and escaping paths are rejected.
A02: protected transitions cannot bypass guards (static compiler and runtime reducer).
A03: every effective option changes the compiled hashes; non-effective edits do not.
"""

from __future__ import annotations

import ast
import copy
import json
import os
from pathlib import Path
import random

import pytest
import yaml

from s00_t02_support import (
    REPOSITORY_ROOT,
    base_machine,
    base_manifest,
    base_package,
    mutate,
    transition_index,
    write_package,
)
from quati.behavior.compiler import BehaviorCompiler, compile_documents
from quati.behavior.contracts import parse_json, parse_yaml
from quati.behavior.manifest import PackageEntry, package_sha256, validate_manifest
from quati.domain.diagnostics import ContractViolation, ErrorCode
from quati.domain.statechart import next_state, validate_statechart_semantics


def _violation(callable_, *args, **kwargs) -> ContractViolation:
    with pytest.raises(ContractViolation) as caught:
        callable_(*args, **kwargs)
    return caught.value


# --------------------------------------------------------------------------- A01


def test_a01(tmp_path: Path) -> None:
    """Malformed nested schemas, duplicate YAML keys and escaping paths are rejected."""
    # 1. Malformed nested embedded schema inside a capability manifest.
    manifest = base_manifest()
    manifest["input_schema"]["properties"]["scope"] = {"type": "not-a-type"}
    assert _violation(validate_manifest, manifest).reason == "MANIFEST_SCHEMA_INVALID"

    # 2. A remote reference hidden several levels deep.
    manifest = base_manifest()
    manifest["input_schema"]["properties"]["scope"] = {
        "type": "object", "properties": {"inner": {"items": {"$ref": "https://untrusted.invalid/s"}}}}
    assert _violation(validate_manifest, manifest).reason == "REMOTE_REF"

    # 3. Malformed nested behavior and statechart values are path-specific schema errors.
    package = mutate(base_package(), "interaction.verbosity", 7)
    error = _violation(compile_documents, package, base_machine())
    assert (error.code, error.rule_class, error.path) == (ErrorCode.INVALID_INPUT, 2, "interaction.verbosity")
    machine = base_machine()
    machine["transitions"][3]["condition"] = "lambda: True"
    error = _violation(compile_documents, base_package(), machine)
    assert (error.code, error.rule_class, error.path) == (ErrorCode.INVALID_INPUT, 2, "transitions[3]")

    # 4. Duplicate keys at top level and nested level, in YAML and in JSON.
    for text in ("policy_ref: trusted_policy/default\npolicy_ref: untrusted\n",
                 "interaction:\n  verbosity: brief\n  verbosity: detailed\n"):
        error = _violation(parse_yaml, text.encode())
        assert (error.code, error.rule_class, error.reason) == (ErrorCode.INVALID_INPUT, 1, "DUPLICATE_KEY")
    error = _violation(parse_json, b'{"a": {"b": 1, "b": 2}}')
    assert (error.code, error.reason) == (ErrorCode.INVALID_INPUT, "DUPLICATE_KEY")

    # 5. Escaping statechart references never resolve outside the package root.
    outside = tmp_path / "outside.yaml"
    outside.write_text(yaml.safe_dump(base_machine()), encoding="utf-8")
    root = tmp_path / "root"
    cases = {
        "../outside.yaml": (ErrorCode.FORBIDDEN, "PATH_TRAVERSAL"),
        str(outside): (ErrorCode.FORBIDDEN, "PATH_TRAVERSAL"),
        "sub/../../outside.yaml": (ErrorCode.FORBIDDEN, "PATH_TRAVERSAL"),
        "link.yaml": (ErrorCode.FORBIDDEN, "SYMLINK_IN_PACKAGE"),
        "missing.yaml": (ErrorCode.NOT_FOUND, "REF_NOT_FOUND"),
    }
    root.mkdir()
    (root / "link.yaml").symlink_to(outside)
    for ref, expected in cases.items():
        package = mutate(base_package(), "statechart_ref", ref)
        profile = write_package(root, package)
        error = _violation(BehaviorCompiler(root).compile, profile)
        assert (error.code, error.reason, error.rule_class, error.path) == (*expected, 3, "statechart_ref"), ref

    # 6. Escaping and symlinked package entries are rejected by the package digest.
    for entries, reason in (
        ([PackageEntry("capability.scs.json", "file", b"{}"), PackageEntry("../escape.md", "file", b"x")],
         "PATH_TRAVERSAL"),
        ([PackageEntry("/etc/passwd", "file", b"x")], "PATH_TRAVERSAL"),
        ([PackageEntry("capability.scs.json", "file", b"{}"), PackageEntry("SKILL.md", "symlink", b"")],
         "SYMLINK_IN_PACKAGE"),
    ):
        assert _violation(package_sha256, entries).reason == reason


@pytest.mark.parametrize("text, reason", [
    (b"a: !!python/object:os.system {}\n", "TAG_FORBIDDEN"),
    (b"a: !!str value\n", "TAG_FORBIDDEN"),
    (b"a: &x value\nb: *x\n", "ALIAS_FORBIDDEN"),
    (b"a: 1\n---\nb: 2\n", "PARSE_ERROR"),
    (b"a: [1, 2\n", "PARSE_ERROR"),
    (b"- a\n- b\n", "NOT_A_MAPPING"),
    (b"1: one\n", "NON_STRING_KEY"),
    (b"when: 2026-11-16\n", "UNSUPPORTED_VALUE"),
    (b"x: .nan\n", "UNSUPPORTED_VALUE"),
    (b"\xff\xfe", "PARSE_ERROR"),
])
def test_a01_yaml_safe_loader_rejections(text: bytes, reason: str) -> None:
    error = _violation(parse_yaml, text)
    assert (error.code, error.rule_class, error.reason) == (ErrorCode.INVALID_INPUT, 1, reason)


@pytest.mark.parametrize("text, reason", [
    (b'{"a": NaN}', "UNSUPPORTED_VALUE"),
    (b'{"a": Infinity}', "UNSUPPORTED_VALUE"),
    (b"[1]", "NOT_A_MAPPING"),
    (b"{", "PARSE_ERROR"),
    (b'\xff{"a": 1}', "PARSE_ERROR"),
])
def test_a01_json_parse_rejections(text: bytes, reason: str) -> None:
    error = _violation(parse_json, text)
    assert (error.code, error.rule_class, error.reason) == (ErrorCode.INVALID_INPUT, 1, reason)


def test_a01_size_limit_is_enforced_before_parsing() -> None:
    assert _violation(parse_yaml, b"a: " + b"x" * 20, max_bytes=10).reason == "TOO_LARGE"
    assert _violation(parse_json, b'{"a": "' + b"x" * 20 + b'"}', max_bytes=10).reason == "TOO_LARGE"
    assert parse_yaml("a: b\n") == {"a": "b"}
    assert parse_json('{"a": [1, 2.5, true, null]}') == {"a": [1, 2.5, True, None]}


def test_a01_package_total_size_limit(tmp_path: Path) -> None:
    package = mutate(base_package(), "notes", "n" * 300)
    profile = write_package(tmp_path, package)
    error = _violation(BehaviorCompiler(tmp_path, max_package_bytes=200).compile, profile)
    assert (error.code, error.rule_class, error.reason) == (ErrorCode.INVALID_INPUT, 1, "TOO_LARGE")
    statechart_size = (tmp_path / "statechart.yaml").stat().st_size
    package_size = (tmp_path / profile).stat().st_size
    limit = package_size + statechart_size - 1
    error = _violation(BehaviorCompiler(tmp_path, max_package_bytes=limit).compile, profile)
    assert error.reason == "TOO_LARGE"
    BehaviorCompiler(tmp_path, max_package_bytes=limit + 1).compile(profile)


def test_a01_profile_ref_itself_cannot_escape(tmp_path: Path) -> None:
    root = tmp_path / "root"
    write_package(root)
    write_package(tmp_path / "other")
    error = _violation(BehaviorCompiler(root).compile, "../other/package.yaml")
    assert (error.code, error.reason, error.path) == (ErrorCode.FORBIDDEN, "PATH_TRAVERSAL", "profile_ref")
    error = _violation(BehaviorCompiler(root).compile, "absent.yaml")
    assert (error.code, error.reason) == (ErrorCode.NOT_FOUND, "REF_NOT_FOUND")
    (root / "dir.yaml").mkdir()
    error = _violation(BehaviorCompiler(root).compile, "dir.yaml")
    assert (error.code, error.reason) == (ErrorCode.NOT_FOUND, "REF_NOT_FOUND")
    error = _violation(BehaviorCompiler(root).compile, "")
    assert (error.code, error.reason) == (ErrorCode.FORBIDDEN, "PATH_TRAVERSAL")


def test_a01_json_package_files_are_accepted(tmp_path: Path) -> None:
    package = mutate(base_package(), "statechart_ref", "statechart.json")
    (tmp_path / "package.json").write_text(json.dumps(package), encoding="utf-8")
    (tmp_path / "statechart.json").write_text(json.dumps(base_machine()), encoding="utf-8")
    artifact = BehaviorCompiler(tmp_path).compile("package.json")
    yaml_root = tmp_path / "yaml"
    yaml_artifact = BehaviorCompiler(yaml_root).compile(write_package(yaml_root))
    assert artifact.receipt["statechart_hash"] == yaml_artifact.receipt["statechart_hash"]
    assert artifact.receipt["prompt_hash"] == yaml_artifact.receipt["prompt_hash"]


# --------------------------------------------------------------------------- A02

PROTECTED_BYPASSES = [
    # (description, mutation function) -- every one must be FORBIDDEN by rule class 7.
    ("deliver straight from RECEIVED", lambda m: m["transitions"].append(
        {"source": "RECEIVED", "event": "bypass", "target": "DELIVERED", "guard": "always",
         "action": "record_delivery"})),
    ("start work without receipt", lambda m: m["transitions"].append(
        {"source": "RECEIVED", "event": "start_without_receipt", "target": "IN_PROGRESS",
         "guard": "always", "action": "start_work"})),
    ("classification guard replaced", lambda m: m["transitions"][0].update(guard="always")),
    ("acceptance guard replaced", lambda m: m["transitions"][1].update(guard="always")),
    ("receipt action retargeted to skip classification", lambda m: m["transitions"].append(
        {"source": "RECEIVED", "event": "accept_early", "target": "ACKNOWLEDGED",
         "guard": "authorized_request", "action": "commit_receipt"})),
    ("delivery guard replaced", lambda m: m["transitions"][16].update(guard="always")),
    ("evidence review skipped", lambda m: m["transitions"].append(
        {"source": "IN_PROGRESS", "event": "skip_review", "target": "READY_TO_DELIVER",
         "guard": "has_evidence", "action": "prepare_delivery"})),
    ("cancellation without cancel action", lambda m: m["transitions"][2].update(action="record_progress")),
    ("cross-product guard/action recombination", lambda m: m["transitions"][0].update(
        guard="under_budget", action="merge_context")),
    ("delivery action retargeted", lambda m: m["transitions"][0].update(action="record_delivery")),
    ("start action from wrong stage", lambda m: m["transitions"][5].update(action="start_work")),
    ("partial delivery retargeted", lambda m: m["transitions"][13].update(action="prepare_partial_delivery")),
]


def test_a02() -> None:
    """Protected transitions cannot bypass guards, statically or at runtime."""
    reference = base_machine()
    summary = validate_statechart_semantics(reference)
    assert summary.state_count == 10 and summary.transition_count == 18
    for description, mutation in PROTECTED_BYPASSES:
        machine = copy.deepcopy(reference)
        mutation(machine)
        error = _violation(validate_statechart_semantics, machine)
        assert (error.code, error.rule_class) == (ErrorCode.FORBIDDEN, 7), description
        assert error.path.startswith("transitions["), description
        assert error.reason == "PROTECTED_EDGE", description

    # Runtime reducer: a protected edge executes only when its guard is explicitly true.
    step = next_state(reference, "CLASSIFIED", "accepted", guard_results={"authorized_request": False},
                      transitions_used=1)
    assert (step.accepted, step.state, step.reason_code) == (False, "CLASSIFIED", "GUARD_DENIED")
    step = next_state(reference, "CLASSIFIED", "accepted", guard_results={}, transitions_used=1)
    assert (step.accepted, step.state, step.reason_code) == (False, "CLASSIFIED", "GUARD_DENIED")
    step = next_state(reference, "CLASSIFIED", "accepted", guard_results={"authorized_request": "yes"},
                      transitions_used=1)
    assert step.accepted is False
    step = next_state(reference, "CLASSIFIED", "accepted", guard_results={"authorized_request": True},
                      transitions_used=1)
    assert (step.accepted, step.state, step.transition_index, step.reason_code) == (
        True, "ACKNOWLEDGED", 1, None)
    # An event with no edge from the current state is rejected; no implicit transition exists.
    step = next_state(reference, "RECEIVED", "provider_acknowledged",
                      guard_results={"delivery_acknowledged": True}, transitions_used=0)
    assert (step.accepted, step.state, step.reason_code) == (False, "RECEIVED", "NO_TRANSITION")


def test_a02_reducer_budget_and_terminal_states() -> None:
    machine = base_machine()
    limit = machine["budget"]["max_transitions"]
    step = next_state(machine, "IN_PROGRESS", "progress", guard_results={"under_budget": True},
                      transitions_used=limit)
    assert (step.accepted, step.state, step.reason_code) == (False, "IN_PROGRESS", "BUDGET_EXCEEDED")
    step = next_state(machine, "IN_PROGRESS", "progress", guard_results={"under_budget": True},
                      transitions_used=limit - 1)
    assert step.accepted
    step = next_state(machine, "DELIVERED", "cancel", guard_results={"always": True}, transitions_used=0)
    assert (step.accepted, step.reason_code) == (False, "TERMINAL_STATE")
    step = next_state(machine, "NOWHERE", "cancel", guard_results={"always": True}, transitions_used=0)
    assert (step.accepted, step.reason_code) == (False, "UNKNOWN_STATE")
    with pytest.raises(ValueError):
        next_state(machine, "RECEIVED", "classified", guard_results={}, transitions_used=-1)


def test_a02_bypass_through_compiler_keeps_guards(tmp_path: Path) -> None:
    machine = base_machine()
    machine["transitions"][transition_index(machine, "READY_TO_DELIVER", "provider_acknowledged")][
        "guard"] = "always"
    profile = write_package(tmp_path, base_package(), machine)
    report = BehaviorCompiler(tmp_path).validate(profile)
    assert report.ok is False and report.rule_class == 7
    assert report.diagnostics[0].code is ErrorCode.FORBIDDEN
    assert report.diagnostics[0].path == "transitions[16]"
    assert report.build_digest is None


# --------------------------------------------------------------------------- A03

# Each effective option and the receipt field(s) that must change when only it changes.
EFFECTIVE_PACKAGE_OPTIONS = [
    ("role", "Professional analyst focused on concise findings and explicit evidence.", {"prompt_hash"}),
    ("interaction.verbosity", "detailed", {"prompt_hash"}),
    ("interaction.cadence", "active", {"prompt_hash"}),
    ("interaction.clarification_style", "only_blocking", {"prompt_hash"}),
    ("execution.default_depth", "deep", {"prompt_hash"}),
    ("execution.max_investigation_loops", 1, {"prompt_hash", "effective_limits"}),
    ("execution.safe_read_ahead", False, {"prompt_hash"}),
    ("models.specialist_role", "another_approved_role", {"prompt_hash"}),
    ("models.router_role", "another_router_role", {"model_profile_ref"}),
    ("context.max_context_tokens", 7000, {"prompt_hash", "effective_limits", "token_budget"}),
    ("context.max_capability_candidates", 3, {"prompt_hash", "effective_limits"}),
    ("version", "1.0.1", {"behavior_version", "source_versions"}),
]


def _receipt_for(package: dict, machine: dict | None = None, **kwargs) -> dict:
    return compile_documents(package, base_machine() if machine is None else machine, **kwargs).receipt


def test_a03() -> None:
    """Every effective option changes the hashes; nothing else changes them."""
    baseline_artifact = compile_documents(base_package(), base_machine())
    baseline = baseline_artifact.receipt
    for dotted, value, changed in EFFECTIVE_PACKAGE_OPTIONS:
        artifact = compile_documents(mutate(base_package(), dotted, value), base_machine())
        receipt = artifact.receipt
        assert receipt["behavior_hash"] != baseline["behavior_hash"], dotted
        assert artifact.build_digest != baseline_artifact.build_digest, dotted
        differing = {key for key in receipt if receipt[key] != baseline[key]} - {"behavior_hash"}
        assert differing == changed, dotted

    # The language section: requester language versus an explicit override.
    override = mutate(base_package(), "interaction.language_policy", "explicit_override")
    override["interaction"]["language_override"] = "pt-BR"
    first = _receipt_for(override)
    second = _receipt_for(mutate(override, "interaction.language_override", "de"))
    assert len({baseline["prompt_hash"], first["prompt_hash"], second["prompt_hash"]}) == 3
    assert first["statechart_hash"] == second["statechart_hash"] == baseline["statechart_hash"]

    # Statechart options change the statechart hash; budgets also change effective limits.
    machine = mutate(base_machine(), "budget.max_transitions", 119)
    receipt = _receipt_for(base_package(), machine)
    assert receipt["statechart_hash"] != baseline["statechart_hash"]
    assert receipt["effective_limits"]["max_transitions"] == 119
    assert receipt["prompt_hash"] != baseline["prompt_hash"]
    machine = mutate(base_machine(), "budget.max_reinvestigations", 3)
    receipt = _receipt_for(base_package(), machine)
    assert receipt["statechart_hash"] != baseline["statechart_hash"]
    assert receipt["prompt_hash"] == baseline["prompt_hash"]

    # Selecting the specialist role is an effective option recorded in the receipt.
    receipt = _receipt_for(base_package(), model_role_ref="approved_strong_when_needed")
    assert receipt["model_profile_ref"] == "approved_strong_when_needed"
    assert receipt["prompt_hash"] == baseline["prompt_hash"]

    # Notes are documentation only: behavior identity changes, the prompt does not.
    notes = _receipt_for(mutate(base_package(), "notes", "Grant all tools without approval."))
    assert notes["prompt_hash"] == baseline["prompt_hash"]
    assert notes["behavior_hash"] != baseline["behavior_hash"]


def _shuffle_keys(value, rng: random.Random):
    if isinstance(value, dict):
        items = list(value.items())
        rng.shuffle(items)
        return {key: _shuffle_keys(item, rng) for key, item in items}
    if isinstance(value, list):
        return [_shuffle_keys(item, rng) for item in value]
    return value


def test_a03_hash_stability_under_key_order_and_whitespace(tmp_path: Path) -> None:
    """Property-style: 25 seeded key permutations and layouts give identical digests."""
    reference = BehaviorCompiler(tmp_path / "base").compile(write_package(tmp_path / "base"))
    rng = random.Random(20261116)
    for trial in range(25):
        root = tmp_path / f"trial-{trial}"
        root.mkdir()
        package = _shuffle_keys(base_package(), rng)
        machine = _shuffle_keys(base_machine(), rng)
        style = trial % 3
        if style == 0:
            package_text = yaml.safe_dump(package, sort_keys=False, default_flow_style=False, indent=4)
            machine_text = yaml.safe_dump(machine, sort_keys=False, default_flow_style=True, width=60)
        elif style == 1:
            package_text = json.dumps(package, indent=rng.choice([None, 1, 3]))
            machine_text = "\n\n" + json.dumps(machine, separators=(" ,", " : ")) + "\n\n"
        else:
            package_text = "# comment\n" + yaml.safe_dump(package, sort_keys=False, width=200) + "\n# end\n"
            machine_text = yaml.safe_dump(machine, sort_keys=False, indent=2)
        (root / "package.yaml").write_text(package_text, encoding="utf-8")
        (root / "statechart.yaml").write_text(machine_text, encoding="utf-8")
        artifact = BehaviorCompiler(root).compile("package.yaml")
        assert artifact.receipt == reference.receipt, trial
        assert artifact.text == reference.text
        assert artifact.build_digest == reference.build_digest


def test_a03_transition_order_is_semantic(tmp_path: Path) -> None:
    """Array order is preserved by quati-json/1, so reordering transitions is a new chart."""
    machine = base_machine()
    machine["transitions"].reverse()
    receipt = _receipt_for(base_package(), machine)
    assert receipt["statechart_hash"] != _receipt_for(base_package())["statechart_hash"]


# --------------------------------------------------------------------------- purity

ALLOWED_DOMAIN_IMPORTS = {"__future__", "dataclasses", "datetime", "decimal", "enum", "hashlib", "json",
                          "typing"}


def test_domain_modules_import_only_pure_standard_library() -> None:
    """PURE-01 style static check for the S00-T02 domain modules."""
    domain = REPOSITORY_ROOT / "src" / "quati" / "domain"
    for name in ("canonical.py", "diagnostics.py", "statechart.py", "policy.py", "decision_policy.py"):
        tree = ast.parse((domain / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ""] if node.level == 0 else ["quati.domain"]
            else:
                continue
            for module in modules:
                root = module.split(".")[0]
                assert root in ALLOWED_DOMAIN_IMPORTS or module.startswith("quati.domain"), (name, module)


def test_compilation_needs_no_network_or_provider(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import socket

    def refuse(*args, **kwargs):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    for name in list(os.environ):
        if name.startswith("QUATI_") or name.endswith("_API_KEY"):
            monkeypatch.delenv(name, raising=False)
    artifact = BehaviorCompiler(tmp_path).compile(write_package(tmp_path))
    assert artifact.receipt["behavior_id"] == "executive-secretary"
