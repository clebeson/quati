"""S00-T03 fail-closed edges at L1: invoke guards 4-11, registry refusals and store faults
(M14-FR-01/03, M15-FR-03, M25-FR-03). Every refusal asserts that no handler ran.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from s00_t03_support import AGENT, OTHER_TENANT, TENANT, build, context, manifest_copy, policy_document, write_package

from quati.adapters.capability_store import FileRegistryStore, default_registry_root
from quati.adapters.fixture_capabilities import (FIXTURE_HANDLERS, FixtureHandler, FixtureHandlerRegistry,
                                                 fixture_manifest)
from quati.application.discovery_tools import execute_tool_call
from quati.application.providers import ToolCall
from quati.domain.capability_registry import Refusal
from quati.domain.policy import PolicyState, policy_version

QUERY = "weekly order volume forecast north region"
ARGS = {"region": "south", "horizon_weeks": 1}


def flaky(arguments, *, now):
    """Passes its self-test (north) and misbehaves for the south region."""
    if arguments["region"] == "south" and arguments.get("horizon_weeks") == 1:
        raise RuntimeError("fixture fault")
    if arguments["region"] == "south":
        return {"region": "south", "method": "wrong", "forecast": [], "evidence_refs": [], "label": "FIXTURE_RESULT"}
    return {"region": arguments["region"], "method": "least_squares_linear_trend", "forecast": [],
            "evidence_refs": ["fixture-dataset:untrusted"], "label": "FIXTURE_RESULT"}


def harness_with(tmp_path: Path, **kwargs):
    handlers = FixtureHandlerRegistry({**FIXTURE_HANDLERS, "flaky": FixtureHandler(
        "flaky", "fixtures.forecast-lime", flaky, {"region": "north", "horizon_weeks": 1}, ())})
    return build(tmp_path, handlers=handlers, **kwargs)


def invoke(harness, arguments, *, turn=None):
    turn = turn or harness.turn()
    turn.search(turn.context, QUERY)
    return turn, turn.invoke(turn.context, "fixtures.forecast-lime", arguments, "key")


def test_handler_failure_bad_output_and_unverified_outcome(tmp_path: Path) -> None:
    harness = harness_with(tmp_path)
    harness.install("forecast-lime", handler="flaky")
    _turn, failed = invoke(harness, ARGS)
    assert (failed.status, failed.reason, failed.trace["handler_executed"]) == ("UNAVAILABLE", "HANDLER_FAILED", True)
    _turn, invalid = invoke(harness, {"region": "south", "horizon_weeks": 2})
    assert (invalid.status, invalid.code, invalid.reason) == ("BLOCKED", "OUTPUT_INVALID", "RESULT_SCHEMA_INVALID")
    _turn, partial = invoke(harness, {"region": "north", "horizon_weeks": 2})
    assert (partial.status, partial.code, partial.reason) == ("PARTIAL", "EVIDENCE_INSUFFICIENT", "OUTCOME_UNVERIFIED")
    assert partial.data["outcome_verification"] == "UNVERIFIED" and partial.uncertainties == ("OUTCOME_UNVERIFIED",)


def test_outcome_verification_none_is_not_required(tmp_path: Path) -> None:
    harness = build(tmp_path)
    manifest = manifest_copy("forecast-lime")
    manifest["outcome_verification"] = {"mode": "none"}
    write_package(tmp_path / "pkg", manifest)
    harness.registry.install(harness.operator, tmp_path / "pkg", source="file:///s", fixture_handler="forecast-lime",
                             enable_fixture=True)
    _turn, result = invoke(harness, {"region": "north", "horizon_weeks": 1})
    assert (result.status, result.data["outcome_verification"]) == ("SUCCEEDED", "NOT_REQUIRED")


def test_policy_approval_required_blocks_reads(tmp_path: Path) -> None:
    document = policy_document()
    document["rules"][0]["verdict"] = "APPROVAL_REQUIRED"
    document["rules"][0]["approver"] = {"rule": "SELF"}
    state = PolicyState.from_document(document, tenant_id=TENANT, trusted_version=policy_version(document))
    harness = build(tmp_path, policy_state=state)
    harness.install("forecast-lime")
    _turn, result = invoke(harness, {"region": "north", "horizon_weeks": 1})
    assert (result.status, result.code, result.reason) == ("BLOCKED", "APPROVAL_REQUIRED", "read-own-spaces")
    assert harness.handlers.total_invocations() == 0


def test_invoke_rechecks_grants_and_model_features(tmp_path: Path) -> None:
    harness = build(tmp_path)
    manifest = manifest_copy("forecast-lime")
    manifest["compatibility"] = {"requires_models": ["tool_calling"]}
    write_package(tmp_path / "pkg", manifest)
    harness.registry.install(harness.operator, tmp_path / "pkg", source="file:///s", fixture_handler="forecast-lime",
                             enable_fixture=True)
    turn = harness.turn(features={"tool_calling"})
    turn.search(turn.context, QUERY)
    turn.model_features = frozenset()            # the turn's model changed after the shortlist
    assert turn.invoke(turn.context, "fixtures.forecast-lime", ARGS).reason == "MODEL_INCOMPATIBLE"
    turn.model_features = frozenset({"tool_calling"})
    harness.grants.permissions = frozenset()     # grant revoked after the shortlist
    assert turn.invoke(turn.context, "fixtures.forecast-lime", ARGS).reason == "NOT_AUTHORIZED"
    assert harness.handlers.total_invocations() == 0


def test_direct_port_calls_with_wrong_types_and_budget(tmp_path: Path) -> None:
    harness = build(tmp_path)
    harness.install("calendar-read")
    turn = harness.turn()
    assert turn.search(turn.context, 5).reason == "TOOL_CALL_MALFORMED"
    assert turn.describe(turn.context, 5).reason == "TOOL_CALL_MALFORMED"
    assert turn.invoke(turn.context, "fixtures.calendar-read", []).reason == "TOOL_CALL_MALFORMED"
    stranger = context(actor="01JD00000000000000000000ZZ")
    for result in (turn.describe(stranger, "fixtures.calendar-read"), turn.invoke(stranger, "fixtures.calendar-read",
                                                                                  {}), turn.status(stranger, "x")):
        assert result.reason == "CONTEXT_MISMATCH"
    _text, step = execute_tool_call(turn, turn.context, ToolCall("quati_search", {"query": {1, 2}}))
    assert (step["reason"], step["arguments_digest"]) == ("TOOL_CALL_MALFORMED", None)
    assert turn.status(turn.context, 7).reason == "EXECUTION_NOT_FOUND"
    assert turn.status(turn.context, "exec-missing").reason == "EXECUTION_NOT_FOUND"
    _text, step = execute_tool_call(turn, turn.context, ToolCall("quati_invoke", {"capability_id": "NONE_FITS",
                                                                                  "input": {}}))
    assert step["reason"] == "BUDGET_EXCEEDED"


def test_registry_refusals(tmp_path: Path) -> None:
    harness = build(tmp_path)
    harness.install("calendar-write")                         # stays DRAFT
    ref, write_ref = "fixtures.calendar-read@1.0.0", "fixtures.calendar-write@1.0.0"
    with pytest.raises(Refusal) as draft:
        harness.registry.bind(harness.operator, write_ref, harness.registry.fixture_binding(write_ref, "calendar-write"))
    assert draft.value.reason == "BINDING_CHECK_FAILED"
    harness.install("calendar-read", handler=None)            # VALIDATED, no binding
    agent = context(actor=AGENT, kind="AGENT")
    for binding, reason in (({"id": "x"}, "BINDING_CHECK_FAILED"),
                            (harness.registry.fixture_binding(write_ref, "calendar-read"), "BINDING_CHECK_FAILED")):
        with pytest.raises(Refusal) as refused:
            harness.registry.bind(harness.operator, ref, binding)
        assert refused.value.reason == reason
    harness.registry.bind(harness.operator, ref, harness.registry.fixture_binding(ref, "calendar-read"))
    with pytest.raises(Refusal) as duplicate:
        harness.registry.bind(harness.operator, ref, harness.registry.fixture_binding(ref, "calendar-read"))
    assert duplicate.value.reason == "BINDING_CHECK_FAILED"
    for call in (lambda: harness.registry.bind(agent, ref, {}), lambda: harness.registry.unbind(agent, "x"),
                 lambda: harness.registry.set_binding_health(agent, "x", healthy=True)):
        with pytest.raises(Refusal) as operator:
            call()
        assert operator.value.reason == "OPERATOR_REQUIRED"
    with pytest.raises(Refusal) as missing:
        harness.registry.unbind(harness.operator, "fixtures.calendar-read@1.0.0#nope")
    assert missing.value.reason == "BINDING_NOT_FOUND"
    before = harness.registry.record(harness.operator, ref)
    harness.registry.unbind(harness.operator, harness.registry.binding_refs(harness.operator, ref)[0])
    assert harness.registry.record(harness.operator, ref) == before   # VALIDATED: nothing to expire
    write_package(tmp_path / "agent-pkg", manifest_copy("mail-search"))
    by_agent = harness.registry.install(agent, tmp_path / "agent-pkg", source="file:///s",
                                        fixture_handler="mail-search", enable_fixture=True)
    assert (by_agent["status"], by_agent["data"]["lifecycle"]) == ("DENIED", "VALIDATED")   # audit P3
    write_package(tmp_path / "bad-kind", manifest_copy("forecast-quick"))
    with pytest.raises(Refusal) as schema:
        harness.registry.install(harness.operator, tmp_path / "bad-kind", source="file:///s", import_kind="bogus")
    assert schema.value.reason == "RECORD_SCHEMA_INVALID"
    assert harness.registry.register_definition(harness.operator, tmp_path / "missing", source="file:///s")[
        "error"]["message"] == "PACKAGE_NOT_FOUND"
    imported = harness.registry.import_mcp_tool(harness.operator, {"name": "Bad Name"}, server="io.example",
                                                server_version="1.0.0", intents={}, quarantine=tmp_path / "q")
    assert imported["error"]["message"] == "MCP_TOOL_INVALID"


def test_catalog_is_tenant_scoped_and_missing_package_is_not_loadable(tmp_path: Path) -> None:
    harness = build(tmp_path)
    harness.install("calendar-read")
    other = context(tenant=OTHER_TENANT)
    harness.registry.install(other, harness.root / "sources" / "calendar-read", source="fixture:calendar-read")
    assert [e.capability_id for e in harness.registry.catalog(harness.operator).entries] == ["fixtures.calendar-read"]
    import shutil
    shutil.rmtree(harness.store.package_dir("fixtures.calendar-read", "1.0.0"))
    assert harness.registry.catalog(harness.operator).entries[0].loadable is False


def test_store_cas_default_root_and_empty_audit(tmp_path: Path, monkeypatch) -> None:
    store = FileRegistryStore(tmp_path / "s")
    assert store.audit_events() == [] and store.lock_entries() == []
    state = store.load()
    store.commit(state, expected_revision=0)
    with pytest.raises(Refusal) as conflict:
        store.commit(state, expected_revision=0)
    assert conflict.value.reason == "REVISION_CONFLICT"
    monkeypatch.setenv("QUATI_DATA_DIR", str(tmp_path / "data"))
    assert default_registry_root() == tmp_path / "data" / "capabilities"
    assert json.loads(store.registry_path.read_text())["revision"] == 1


def test_fixture_self_tests(tmp_path: Path) -> None:
    registry = FixtureHandlerRegistry({**FIXTURE_HANDLERS, "broken": FixtureHandler(
        "broken", "fixtures.x", lambda arguments, *, now: (_ for _ in ()).throw(RuntimeError()), {"limit": 1}, ()),
        "wrong": FixtureHandler("wrong", "fixtures.x", lambda arguments, *, now: {"nope": 1}, {"limit": 1}, ())})
    from s00_t03_support import START
    for name in ("calendar-write", "forecast-publish"):
        assert registry.self_test(name, fixture_manifest(name), now=START) is not None
    assert registry.self_test("broken", fixture_manifest("calendar-read"), now=START) is None
    assert registry.self_test("wrong", fixture_manifest("calendar-read"), now=START) is None
    assert registry.total_invocations() == 0
