"""S00-T03 audit findings reproduced through the public API (P1-1..P1-4, P2-1..P2-3, tokenization, P3), L1.

Each test is the adversarial probe from the independent audit turned into an assertion that
the trusted code fails closed.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from s00_t03_support import (AGENT, build, context, handlers_with, manifest_copy, trusted_policy_state,
                             write_package)

from quati.adapters.capability_store import empty_state
from quati.domain.capability_registry import Refusal
from quati.domain.discovery import query_terms
from quati.domain.policy import PolicyState


def _custom(harness, capability_id: str, base: str, handler: str, **changes):
    manifest = manifest_copy(base)
    manifest["id"], manifest["name"] = capability_id, capability_id.split(".", 1)[1]
    manifest.update(changes)
    package = write_package(harness.root / "src" / capability_id, manifest)
    return harness.registry.install(harness.operator, package, source="local", fixture_handler=handler,
                                    enable_fixture=True)


def test_p1_1_handler_identity_and_permission_floor(tmp_path: Path) -> None:
    harness = build(tmp_path, grants=frozenset())
    for capability_id in ("evil.reader", "fixtures.calendar-read"):
        result = _custom(harness, capability_id, "calendar-read", "calendar-read", permissions=[])
        assert (result["status"], result["error"]["code"], result["error"]["message"]) == (
            "DENIED", "FORBIDDEN", "HANDLER_IDENTITY_MISMATCH"), capability_id
        assert result["data"]["lifecycle"] == "VALIDATED"
    turn = harness.turn()
    assert turn.search(harness.operator, "next appointment").data["candidates"] == []
    assert turn.invoke(harness.operator, "evil.reader", {"limit": 5}).trace["handler_executed"] is False
    assert harness.handlers.total_invocations() == 0


def test_p1_2_write_handler_never_executes(tmp_path: Path) -> None:
    harness = build(tmp_path)
    for capability_id in ("evil.pub", "fixtures.forecast-publish"):
        result = _custom(harness, capability_id, "forecast-publish", "forecast-publish", effects="read",
                         requires_approval=False, permissions=["forecast.read", "forecast.write"],
                         outcome_verification={"mode": "none"})
        assert result["error"]["message"] == "HANDLER_IDENTITY_MISMATCH", capability_id
    turn = harness.turn()
    assert turn.search(harness.operator, "publish forecast dashboard").data["candidates"] == []
    assert harness.handlers.invocations() == {}


def _three_bindings(tmp_path: Path, unhealthy: int, audit=None):
    harness = build(tmp_path, audit=audit)
    harness.install("forecast-quick", enable=False)
    ref = "fixtures.forecast-quick@1.0.0"
    for suffix in ("b2", "b3"):
        harness.registry.bind(harness.operator, ref, harness.registry.fixture_binding(ref, "forecast-quick",
                                                                                      suffix=suffix))
    record = harness.registry.transition(harness.operator, ref, harness.registry.record(harness.operator, ref)[
        "revision"], "STAGED")
    harness.registry.transition(harness.operator, ref, record["revision"], "ENABLED",
                                approval=harness.registry.fixture_enable_approval(harness.operator, ref))
    for binding_ref in harness.registry.binding_refs(harness.operator, ref)[:unhealthy]:
        harness.registry.set_binding_health(harness.operator, binding_ref, healthy=False)
    return harness


def test_p1_3_selected_binding_is_the_policy_bound_binding(tmp_path: Path) -> None:
    beyond = _three_bindings(tmp_path / "a", unhealthy=2)
    turn = beyond.turn()
    turn.search(beyond.operator, "rough order estimate north")
    result = turn.invoke(beyond.operator, "fixtures.forecast-quick", {"region": "north"})
    assert (result.status, result.reason, beyond.gate.calls) == ("UNAVAILABLE", "BINDING_UNAVAILABLE", 0)
    events: list[dict] = []
    fallback = _three_bindings(tmp_path / "b", unhealthy=1, audit=events.append)
    turn = fallback.turn()
    turn.search(fallback.operator, "rough order estimate north")
    result = turn.invoke(fallback.operator, "fixtures.forecast-quick", {"region": "north"})
    decided = [event for event in events if event["event"] == "policy.decided"][-1]
    assert result.status == "SUCCEEDED"
    assert decided["intent"]["binding_id"] == result.trace["binding_id"] == "fixtures.forecast-quick.b2"
    forged = _three_bindings(tmp_path / "c", unhealthy=1)
    real = forged.gate.decide
    forged.gate.decide = lambda ctx, intent, runtime_profile=None: replace(real(ctx, intent), intent_digest="0" * 64)
    turn = forged.turn()
    turn.search(forged.operator, "rough order estimate north")
    result = turn.invoke(forged.operator, "fixtures.forecast-quick", {"region": "north"})
    assert (result.status, result.reason) == ("DENIED", "narrowed_scope_violation")
    assert forged.handlers.total_invocations() == 0


def test_p1_4_losing_concurrent_install_keeps_the_winner(tmp_path: Path) -> None:
    winner, loser = build(tmp_path), build(tmp_path)
    first = manifest_copy("forecast-quick")
    second = manifest_copy("forecast-quick")
    second["description"] += " Variant two of the package text."
    stale, original, calls = empty_state(), loser.store.load, {"n": 0}

    def load_once():
        calls["n"] += 1
        return stale if calls["n"] == 1 else original()

    loser.store.load = load_once
    won = winner.registry.install(winner.operator, write_package(tmp_path / "s1", first), source="a",
                                  fixture_handler="forecast-quick", enable_fixture=True)
    lost = loser.registry.install(loser.operator, write_package(tmp_path / "s2", second), source="b",
                                  fixture_handler="forecast-quick", enable_fixture=True)
    assert (won["status"], lost["status"], lost["error"]["code"]) == ("SUCCEEDED", "CONFLICT", "REVISION_CONFLICT")
    fresh = winner.restart()
    record = fresh.registry.record(fresh.operator, "fixtures.forecast-quick@1.0.0")
    assert fresh.store.lock_entries()[0]["sha256"] == record["package_sha256"]
    assert [entry.loadable for entry in fresh.registry.catalog(fresh.operator).entries] == [True]
    turn = fresh.turn()
    assert [c["capability_id"] for c in turn.search(fresh.operator, "rough order estimate").data["candidates"]] == [
        "fixtures.forecast-quick"]


def test_p2_1_replay_is_policy_checked(tmp_path: Path) -> None:
    holder = {"state": trusted_policy_state()}
    harness = build(tmp_path)
    harness.gate.policy_state_provider = lambda: holder["state"]
    harness.install("forecast-quick")
    turn = harness.turn()
    turn.search(harness.operator, "rough order estimate")
    first = turn.invoke(harness.operator, "fixtures.forecast-quick", {"region": "north"})
    holder["state"] = PolicyState.unavailable("loader_error")
    calls = harness.gate.calls
    replay = turn.invoke(harness.operator, "fixtures.forecast-quick", {"region": "north"})
    assert (first.status, replay.status, replay.reason) == ("SUCCEEDED", "DENIED", "policy_unavailable")
    assert harness.gate.calls == calls + 1 and "output" not in (replay.data or {})


def test_p2_2_tampered_registry_manifest_is_not_loadable(tmp_path: Path) -> None:
    harness = build(tmp_path, grants=frozenset())
    harness.install("calendar-read")
    state = json.loads(harness.store.registry_path.read_text())
    state["definitions"][0]["manifest"]["permissions"] = []
    harness.store.registry_path.write_text(json.dumps(state))
    restarted = harness.restart()
    turn = restarted.turn()
    assert turn.search(restarted.operator, "next appointment").data["candidates"] == []
    assert [entry.loadable for entry in restarted.registry.catalog(restarted.operator).entries] == [False]


def test_p2_3_shortlist_is_union_capped_at_five(tmp_path: Path) -> None:
    words = ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf")
    ids = [f"fixtures.forecast-{word}" for word in words]
    harness = build(tmp_path, handlers=handlers_with(*ids))
    for word, capability_id in zip(words, ids):
        manifest = manifest_copy("forecast-lime")
        manifest["id"], manifest["name"] = capability_id, f"forecast-{word}"
        manifest["description"] += f" Codename {word}."
        harness.registry.install(harness.operator, write_package(tmp_path / word, manifest), source="local",
                                 fixture_handler=capability_id.split(".", 1)[1], enable_fixture=True)
    turn = harness.turn()
    first = turn.search(harness.operator, "alpha bravo charlie")
    second = turn.search(harness.operator, "delta echo foxtrot golf", 5)
    returned = [c["capability_id"] for result in (first, second) for c in result.data["candidates"]]
    assert len(set(returned)) == 7 and list(turn.shortlist) == list(dict.fromkeys(returned))[:5]
    outside = next(cid for cid in returned if cid not in turn.shortlist)
    assert turn.invoke(harness.operator, outside, {"region": "north", "horizon_weeks": 1}).reason == "NOT_IN_SHORTLIST"


def test_tokenization_folds_diacritics_both_ways(tmp_path: Path) -> None:
    assert query_terms("Reunião PRÓXIMA, ﬁm!") == ("reuniao", "proxima", "fim")
    harness = build(tmp_path, handlers=handlers_with("fixtures.reunion-notes", "fixtures.plain-notes"))
    for capability_id, word in (("fixtures.reunion-notes", "reunião"), ("fixtures.plain-notes", "reuniao")):
        manifest = manifest_copy("forecast-lime")
        manifest["id"], manifest["name"] = capability_id, capability_id.split(".", 1)[1]
        manifest["description"] = f"Synthetic notes fixture that mentions the word {word} for tokenizer tests."
        harness.registry.install(harness.operator, write_package(tmp_path / capability_id, manifest), source="l",
                                 fixture_handler=capability_id.split(".", 1)[1], enable_fixture=True)
    for query in ("reuniao", "REUNIÃO"):
        turn = harness.turn()
        found = sorted(c["capability_id"] for c in turn.search(harness.operator, query).data["candidates"])
        assert found == ["fixtures.plain-notes", "fixtures.reunion-notes"], query
    turn = harness.turn()
    assert turn.search(harness.operator, 'reuniao" OR "*').status == "SUCCEEDED"   # operators are never parsed


def test_p3_agent_cannot_stage_and_audit_is_write_ahead(tmp_path: Path) -> None:
    harness = build(tmp_path)
    agent = context(actor=AGENT, kind="AGENT")
    package = write_package(tmp_path / "pkg", manifest_copy("forecast-quick"))
    result = harness.registry.install(agent, package, source="local", fixture_handler="forecast-quick")
    assert (result["status"], result["error"]["message"], result["data"]["lifecycle"]) == (
        "DENIED", "OPERATOR_REQUIRED", "VALIDATED")
    ref = "fixtures.forecast-quick@1.0.0"
    with pytest.raises(Refusal) as bind:
        harness.registry.bind(agent, ref, harness.registry.fixture_binding(ref, "forecast-quick"))
    assert bind.value.reason == "OPERATOR_REQUIRED"
    harness.registry.bind(harness.operator, ref, harness.registry.fixture_binding(ref, "forecast-quick"))
    with pytest.raises(Refusal) as stage:
        harness.registry.transition(agent, ref, harness.registry.record(harness.operator, ref)["revision"], "STAGED")
    assert stage.value.reason == "OPERATOR_REQUIRED"
    crashing = build(tmp_path / "crash")

    def crash(point: str) -> None:
        if point == "registry.before_rename":
            raise RuntimeError("injected crash")

    crashing.store.hook = crash
    with pytest.raises(RuntimeError):
        crashing.install("calendar-read")
    intents = [e for e in crashing.store.audit_events() if e["event"] == "registry.intent"]
    assert intents and intents[-1]["operation"] == "install" and intents[-1]["ref"] == "fixtures.calendar-read@1.0.0"


def test_identity_ok_but_self_test_or_stored_digest_fails_closed(tmp_path: Path) -> None:
    harness = build(tmp_path)
    narrowed = manifest_copy("calendar-read")
    narrowed["input_schema"]["properties"]["limit"]["maximum"] = 0          # the trusted self-test input no longer fits
    result = harness.registry.install(harness.operator, write_package(tmp_path / "n", narrowed), source="l",
                                      fixture_handler="calendar-read", enable_fixture=True)
    assert (result["error"]["message"], result["data"]["lifecycle"]) == ("BINDING_CHECK_FAILED", "VALIDATED")
    other = build(tmp_path / "other")
    other.install("forecast-quick", handler=None)
    ref = "fixtures.forecast-quick@1.0.0"
    stored = other.store.package_dir("fixtures.forecast-quick", "1.0.0") / "capability.scs.json"
    stored.write_bytes(stored.read_bytes().replace(b"forecast.read", b"forecast.none"))
    with pytest.raises(Refusal) as tampered:
        other.registry.bind(other.operator, ref, other.registry.fixture_binding(ref, "forecast-quick"))
    assert tampered.value.reason == "DIGEST_MISMATCH"


def test_reinstall_repairs_an_unpublished_package_and_store_package_is_locked(tmp_path: Path) -> None:
    import shutil
    harness = build(tmp_path)
    harness.install("forecast-quick")
    shutil.rmtree(harness.store.package_dir("fixtures.forecast-quick", "1.0.0"))   # crash after CAS, before rename
    assert [entry.loadable for entry in harness.registry.catalog(harness.operator).entries] == [False]
    again = harness.install("forecast-quick")
    assert again["data"]["already_installed"] is True
    assert [entry.loadable for entry in harness.registry.catalog(harness.operator).entries] == [True]
    from quati.behavior.manifest import scan_package_dir
    entries = scan_package_dir(harness.store.package_dir("fixtures.forecast-quick", "1.0.0"))
    sha = harness.store.store_package("fixtures.copy", "1.0.0", entries)
    assert harness.store.package_digest("fixtures.copy", "1.0.0") == sha
