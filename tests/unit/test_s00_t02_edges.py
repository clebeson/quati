"""S00-T02 boundary and fail-closed edge cases (M14, M25, M30 shared enforcement points)."""

from __future__ import annotations

import dataclasses
import json
import os
from datetime import timedelta
from pathlib import Path

import pytest

from s00_t02_support import ACTOR, NOW, TENANT, base_machine, base_manifest, base_package, base_policy, write_package
from quati.behavior.compiler import BehaviorCompiler, compile_documents, diff_documents
from quati.behavior.contracts import ContractCatalog, parse_document
from quati.behavior.manifest import validate_manifest
from quati.behavior.store import BehaviorStore, PromotionApproval
from quati.behavior.trusted_config import load_policy, load_policy_registry
from quati.domain.canonical import CanonicalJsonError, canonical_bytes, digest
from quati.domain.decision_policy import check_decision_policy
from quati.domain.diagnostics import ContractViolation, ErrorCode
from quati.domain.policy import (
    EffectIntent,
    PolicyContext,
    PolicyFileSnapshot,
    PolicyRegistry,
    PolicyState,
    adopt_policy,
    glob_match,
    policy_version,
)
from quati.domain.statechart import next_state, validate_statechart_semantics

UID = os.getuid()


def _violation(callable_, *args, **kwargs) -> ContractViolation:
    with pytest.raises(ContractViolation) as caught:
        callable_(*args, **kwargs)
    return caught.value


def test_canonical_form_rejects_non_json_values() -> None:
    assert canonical_bytes({"b": [1, (2, 3)], "a": None, "c": 1.5}) == b'{"a":null,"b":[1,[2,3]],"c":1.5}'
    for value in (float("nan"), float("inf"), {1: "x"}, {"a": {1, 2}}, b"bytes"):
        with pytest.raises(CanonicalJsonError):
            digest(value)


def test_contract_violation_needs_a_diagnostic() -> None:
    with pytest.raises(ValueError):
        ContractViolation([])


def test_parse_document_by_suffix() -> None:
    assert parse_document("a.YML", b"a: 1\n") == {"a": 1}
    assert parse_document("a.json", b'{"a": 1}') == {"a": 1}
    error = _violation(parse_document, "a.toml", b"a = 1")
    assert (error.code, error.reason, error.rule_class) == (ErrorCode.INVALID_INPUT, "UNSUPPORTED_FORMAT", 1)
    error = _violation(parse_document, "noext", b"a: 1")
    assert error.reason == "UNSUPPORTED_FORMAT"


def test_compiler_rejects_unsupported_package_format(tmp_path: Path) -> None:
    (tmp_path / "package.txt").write_text("id: x\n")
    error = _violation(BehaviorCompiler(tmp_path).compile, "package.txt")
    assert error.reason == "UNSUPPORTED_FORMAT"


def test_catalog_schema_access_and_date_time_format(tmp_path: Path) -> None:
    catalog = ContractCatalog()
    assert catalog.schema("policy.schema.json")["title"].startswith("Quati tenant policy")
    for expires, valid in (("2026-11-16T12:00:00Z", True), ("2026-11-16T12:00:00", False),
                           ("2026-13-40T12:00:00Z", False), ("tomorrow", False)):
        document = base_policy()
        document["rules"][0]["expires_at"] = expires
        assert (not catalog.errors(document, "policy.schema.json")) is valid, expires
    # Non-string values are left to the type keyword.
    document = base_policy()
    document["rules"][0]["expires_at"] = 5
    assert catalog.errors(document, "policy.schema.json")


def test_compile_documents_type_and_diff_edges() -> None:
    with pytest.raises(TypeError):
        compile_documents(base_package(), base_machine(), decision_policy={"schema_version": "x"})
    assert diff_documents({"a": 1}, {"a": 1, "b": 2}) == ("b",)
    assert diff_documents({"a": [1, 2]}, {"a": [1]}) == ("a",)
    assert diff_documents({"a": [1, 2]}, {"a": [1, 3]}) == ("a[1]",)
    assert diff_documents({"a": 1}, {"a": True}) == ("a",)
    assert diff_documents(1, 2) == ("$",)
    assert diff_documents({"a": 1}, {"a": 1}) == ()


def test_manifest_non_object_embedded_schema() -> None:
    manifest = base_manifest()
    manifest["input_schema"] = "not a schema"
    with pytest.raises(ContractViolation) as caught:
        validate_manifest(manifest)
    assert caught.value.reason == "SCHEMA_NO_PROPERTIES"


def test_package_root_must_be_a_directory(tmp_path: Path) -> None:
    from quati.behavior.manifest import load_capability_package

    (tmp_path / "file").write_text("x")
    with pytest.raises(ContractViolation) as caught:
        load_capability_package(tmp_path / "file")
    assert (caught.value.code, caught.value.reason) == (ErrorCode.NOT_FOUND, "PACKAGE_NOT_FOUND")


def _promoted_store(tmp_path: Path):
    store = BehaviorStore(tmp_path / "store")
    root = tmp_path / "pkg"
    write_package(root)
    proposal = store.propose(root, "package.yaml", origin="OPERATOR", author="operator-1")
    report = store.validate(proposal.digest)
    return store, proposal, report


def test_store_integrity_failures(tmp_path: Path) -> None:
    store, proposal, report = _promoted_store(tmp_path)
    objects = tmp_path / "store" / "objects"
    # A tampered source object.
    source = objects / proposal.statechart_object
    original = source.read_bytes()
    source.write_bytes(original.replace(b'"name"', b'"Name"'))
    assert _violation(store.validate, proposal.digest).reason == "DIGEST_MISMATCH"
    source.write_bytes(original)
    # A tampered proposal record.
    record_path = tmp_path / "store" / "proposals" / f"{proposal.digest}.json"
    record = json.loads(record_path.read_text())
    record_path.write_bytes(canonical_bytes(dict(record, author="someone-else")))
    assert _violation(store.proposal_state, proposal.digest).reason == "DIGEST_MISMATCH"
    record_path.write_bytes(b"{not json")
    error = _violation(store.proposal_state, proposal.digest)
    assert (error.code, error.reason) == (ErrorCode.INTERNAL_ERROR, "OBJECT_CORRUPT")
    # An artifact missing fields is treated as altered.
    artifact = objects / f"{report.build_digest}.json"
    artifact.write_text(json.dumps({"text": "x"}))
    assert _violation(store.render, report.build_digest).reason == "DIGEST_MISMATCH"


def test_store_promote_input_guards(tmp_path: Path) -> None:
    store, proposal, report = _promoted_store(tmp_path)
    approval = PromotionApproval(approval_id="apr-1", approver_id=ACTOR, approver_kind="HUMAN",
                                 artifact_digest=report.build_digest, expires_at=NOW + timedelta(minutes=5))
    with pytest.raises(ValueError):
        store.promote(proposal.digest, approval=approval, expected_revision=0, now=NOW.replace(tzinfo=None),
                      verify_approval=lambda a: True)
    with pytest.raises(ValueError):
        PromotionApproval(approval_id="", approver_id=ACTOR, approver_kind="HUMAN",
                          artifact_digest=report.build_digest, expires_at=NOW)
    # A verifier answering a truthy non-True value is not trusted.
    error = _violation(store.promote, proposal.digest, approval=approval, expected_revision=0, now=NOW,
                       verify_approval=lambda a: "yes")
    assert error.reason == "approval_not_trusted"


def test_policy_registry_file_must_be_json(tmp_path: Path) -> None:
    path = tmp_path / "registry.json"
    path.write_bytes(b"{oops")
    path.chmod(0o600)  # the registry file needs the policy-file protections (audit P2)
    error = _violation(load_policy_registry, path, tenant_id=TENANT)
    assert (error.code, error.reason) == (ErrorCode.CONFIG_INVALID, "PARSE_ERROR")


def test_policy_registry_revision_must_match_history() -> None:
    document = {"tenant_id": TENANT, "revision": 3, "versions": []}
    assert _violation(PolicyRegistry.from_json, document).reason == "registry_inconsistent"
    assert _violation(PolicyRegistry.from_json, dict(document, versions="x")).reason == "registry_invalid"


def test_adoption_requires_owner_or_admin_role() -> None:
    snapshot = PolicyFileSnapshot(content=json.dumps(base_policy()).encode(), mode=0o600, owner_uid=UID)
    state = load_policy(snapshot, tenant_id=TENANT, installation_uid=UID, trusted_version=None)
    member = PolicyContext(tenant_id=TENANT, actor_id=ACTOR, principal_kind="HUMAN", tenant_role="MEMBER")
    error = _violation(adopt_policy, PolicyRegistry.empty(TENANT), state, expected_revision=0, actor=member,
                       interactive=True, capability_context=False)
    assert error.reason == "role_not_permitted"


def test_policy_state_rejects_offsetless_expiry_in_domain() -> None:
    document = base_policy()
    document["rules"][0]["expires_at"] = "2026-11-16T12:00:00"
    with pytest.raises(ValueError):
        PolicyState.from_document(document, tenant_id=TENANT, trusted_version=policy_version(document))
    # Through the loader the schema rejects it first; either way the state is unavailable.
    snapshot = PolicyFileSnapshot(content=json.dumps(document).encode(), mode=0o600, owner_uid=UID)
    assert load_policy(snapshot, tenant_id=TENANT, installation_uid=UID, trusted_version=None).cause == \
        "schema_invalid"


def _intent(**overrides) -> dict:
    fields = dict(effect_id="eff-1", actor_id=ACTOR, tenant_id=TENANT, capability_id="research.fixture",
                  capability_version="1.0.0", binding_id="bind-1", binding_version="1", operation="invoke",
                  destination_ref="fixture:local", policy_version="0" * 64, idempotency_key="idem-1",
                  input_digest="1" * 64, effect_class="read", data_class="PUBLIC", integrity="TRUSTED",
                  steering_args_user_confirmed=True)
    fields.update(overrides)
    return fields


def test_effect_intent_wire_edges() -> None:
    with pytest.raises(ContractViolation):
        EffectIntent(**_intent(space_id=""))
    with pytest.raises(ContractViolation):
        EffectIntent.from_wire(["not", "a", "mapping"], integrity="TRUSTED", steering_args_user_confirmed=True)
    wire = EffectIntent(**_intent()).to_wire()
    for bad in ("PUBLIC", "secret", 5):
        with pytest.raises(ContractViolation) as caught:
            EffectIntent.from_wire(dict(wire, data_class=bad), integrity="TRUSTED", steering_args_user_confirmed=True)
        assert caught.value.path == "data_class"


@pytest.mark.parametrize("pattern, value, expected", [
    ("abc*", "abc", True), ("a**", "a", True), ("*", "", True), ("?", "", False), ("a*c", "abd", False),
    ("a*b*c", "aXbYc", True), ("a*b", "ab", True), ("", "", True), ("", "a", False),
])
def test_glob_match(pattern: str, value: str, expected: bool) -> None:
    assert glob_match(pattern, value) is expected


@pytest.mark.parametrize("machine", [
    ["not", "a", "mapping"],
    {"states": [], "terminal": [], "transitions": [], "budget": {"max_transitions": 1, "max_reinvestigations": 0}},
    {"initial": "A", "states": "A", "terminal": [], "transitions": [],
     "budget": {"max_transitions": 1, "max_reinvestigations": 0}},
    {"initial": "A", "states": ["A"], "terminal": [], "transitions": [], "budget": {"max_transitions": True}},
    {"initial": "A", "states": ["A", 1], "terminal": ["A"], "transitions": [],
     "budget": {"max_transitions": 1, "max_reinvestigations": 0}},
    {"initial": "A", "states": ["A"], "terminal": [], "transitions": [{"source": "A"}],
     "budget": {"max_transitions": 1, "max_reinvestigations": 0}},
])
def test_domain_statechart_shape_guard(machine) -> None:
    error = _violation(validate_statechart_semantics, machine)
    assert (error.code, error.rule_class, error.reason) == (ErrorCode.INVALID_INPUT, 2, "SCHEMA_INVALID")
    # The reducer refuses an unvalidated machine instead of executing it.
    with pytest.raises(ContractViolation):
        next_state(machine, "A", "go", guard_results={}, transitions_used=0)


def test_decision_policy_domain_type_edges() -> None:
    error = _violation(check_decision_policy, ["not", "a", "mapping"])
    assert (error.code, error.reason) == (ErrorCode.CONFIG_INVALID, "SCHEMA_INVALID")
    document = {"behavior_policy": {"blocking_fields": ["target_resource", "recipient", "authorization_scope",
                                                        "destructive_or_external_effect_confirmation",
                                                        "deadline_if_stated_relative_and_unresolvable"]},
                "routing_policy": {"candidate_score_weights": {"a": 1}}, "channel_policy": {}}
    error = _violation(check_decision_policy, document)
    assert (error.reason, error.path) == ("SCHEMA_INVALID", "channel_policy")


def test_trusted_policy_context_is_frozen() -> None:
    context = PolicyContext(tenant_id=TENANT, actor_id=ACTOR, principal_kind="HUMAN")
    with pytest.raises(dataclasses.FrozenInstanceError):
        context.tenant_role = "OWNER"  # type: ignore[misc]
