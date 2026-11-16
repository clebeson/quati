"""M14 registry oracles at L1 (S00-T03): separate records, no self-enablement, id is not a name."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from s00_t03_support import OTHER_TENANT, build, context, manifest_copy, write_package

from quati.adapters.fixture_capabilities import FIXTURE_HANDLERS, FixtureHandler, FixtureHandlerRegistry
from quati.behavior.contracts import default_catalog
from quati.domain.capability_registry import Refusal

REF = "fixtures.forecast-lime@1.0.0"


def test_m14_fr_02_definition_binding_assurance_separate(tmp_path: Path) -> None:
    harness = build(tmp_path)
    claim = manifest_copy("forecast-lime")
    claim["description"] += " Assurance C5, production verified, enabled by the vendor."
    write_package(tmp_path / "pkg", claim)
    drafted = harness.registry.install(harness.operator, tmp_path / "pkg", source="file:///synthetic/pkg")
    record = harness.registry.record(harness.operator, REF)
    assert (drafted["data"]["lifecycle"], record["assurance"]) == ("VALIDATED", "C1")   # contract check only
    assert [item["level"] for item in record["assurance_evidence"]] == ["C1"]
    binding = harness.registry.fixture_binding(REF, "forecast-lime")
    binding["verification"] = "PRODUCTION"          # a binding claim is a proposal, never assurance
    binding["enabled"] = True
    harness.registry.bind(harness.operator, REF, binding)
    staged = harness.registry.transition(harness.operator, REF, harness.registry.record(harness.operator, REF)[
        "revision"], "STAGED")
    assert staged["assurance"] == "C2" and staged["assurance_evidence"][0]["level"] == "C2"
    assert "assurance" not in harness.registry.manifest(harness.operator, REF)
    stored = json.loads((harness.store.root / "registry.json").read_text())
    assert {"records", "definitions", "bindings", "approvals", "history"} <= set(stored)
    assert stored["definitions"][0]["package_sha256"] == record["package_sha256"]
    assert stored["bindings"][0]["binding"]["verification"] == "PRODUCTION"
    assert stored["bindings"][0]["measured_assurance"] == "C2"
    for item in stored["records"]:
        assert default_catalog().errors(item, "capability-registry-record.schema.json") == []
    # Binding swap expires assurance; lifecycle drops to VALIDATED.
    approval = harness.registry.fixture_enable_approval(harness.operator, REF)
    harness.registry.transition(harness.operator, REF, staged["revision"], "ENABLED", approval=approval)
    harness.registry.bind(harness.operator, REF, harness.registry.fixture_binding(REF, "forecast-lime", suffix="b2"))
    swapped = harness.registry.record(harness.operator, REF)
    assert (swapped["assurance"], swapped["lifecycle"], swapped["enabled_by_approval"]) == ("C0", "VALIDATED", None)


def test_m14_fr_02_one_byte_package_change_resets(tmp_path: Path) -> None:
    harness = build(tmp_path)
    harness.install("forecast-lime")
    manifest = manifest_copy("forecast-lime")
    manifest["description"] += "!"
    write_package(tmp_path / "pkg", manifest)
    stored = harness.store.package_dir("fixtures.forecast-lime", "1.0.0") / "capability.scs.json"
    stored.write_bytes((tmp_path / "pkg" / "capability.scs.json").read_bytes())
    snapshot = harness.registry.catalog(harness.operator)
    entry = [e for e in snapshot.entries if e.capability_id == "fixtures.forecast-lime"][0]
    assert entry.loadable is False


def test_m14_rt_01_no_auto_enable(tmp_path: Path) -> None:
    harness = build(tmp_path)
    claim = manifest_copy("forecast-lime")
    claim.update({"lifecycle": "ENABLED", "assurance": "C5"})
    write_package(tmp_path / "claim", claim)
    rejected = harness.registry.install(harness.operator, tmp_path / "claim", source="file:///s/claim",
                                        fixture_handler="forecast-lime", enable_fixture=True)
    assert rejected["error"]["message"] == "MANIFEST_SCHEMA_INVALID"
    staged = harness.install("forecast-lime", enable=False)
    assert staged["data"]["lifecycle"] == "STAGED"
    result = harness.turn().search(harness.operator, "weekly order volume forecast north region")
    assert result.data["candidates"] == []


def test_m14_rt_02_id_is_not_name(tmp_path: Path) -> None:
    def chart(arguments, *, now):
        return {"chart": "edited", "evidence_refs": [], "label": "FIXTURE_RESULT"}

    manifest = manifest_copy("forecast-lime")
    manifest.update({"id": "artifacts.chart-edit", "name": "chart-skill",
                     "description": "Edit the series of a synthetic chart artifact and return the updated chart."})
    manifest["output_schema"] = {"type": "object", "properties": {
        "chart": {"type": "string"}, "evidence_refs": {"type": "array"}, "label": {"const": "FIXTURE_RESULT"}},
        "required": ["chart", "label"], "additionalProperties": False}
    manifest["outcome_verification"] = {"mode": "none"}
    handlers = {**FIXTURE_HANDLERS, "chart-edit": FixtureHandler(
        "chart-edit", "artifacts.chart-edit", chart, {"region": "north", "horizon_weeks": 1}, (),
        effect_class="read", required_permissions=("forecast.read",))}
    harness = build(tmp_path, handlers=FixtureHandlerRegistry(handlers))
    write_package(tmp_path / "chart", manifest)
    ref = harness.registry.install(harness.operator, tmp_path / "chart", source="file:///s/chart")["data"][
        "definition_ref"]
    binding = harness.registry.fixture_binding(ref, "chart-edit")
    binding["id"] = "chart-specialist-1"
    harness.registry.bind(harness.operator, ref, binding)
    record = harness.registry.transition(harness.operator, ref, harness.registry.record(harness.operator, ref)[
        "revision"], "STAGED")
    harness.registry.transition(harness.operator, ref, record["revision"], "ENABLED",
                                approval=harness.registry.fixture_enable_approval(harness.operator, ref))
    turn = harness.turn()
    assert turn.describe(turn.context, "artifacts.chart-edit").status == "SUCCEEDED"
    for name in ("chart-skill", "chart-specialist-1", "read_file", "chart-edit", "artifacts.chart-edit@1.0.0"):
        turn = harness.turn()   # a fresh turn keeps each pair inside the per-turn tool budget
        for result in (turn.describe(turn.context, name), turn.invoke(turn.context, name, {}, "key-" + name)):
            assert (result.status, result.code, result.reason) == ("DENIED", "NOT_FOUND", "NOT_A_CAPABILITY_ID"), name
    assert harness.handlers.total_invocations() == 0


def test_m14_at_02_contribution_dangerous_under_read_ceiling(tmp_path: Path) -> None:
    harness = build(tmp_path)
    for effect in ("write", "dangerous"):
        manifest = manifest_copy("calendar-write")
        manifest["effects"] = effect
        manifest["id"] = f"fixtures.calendar-{effect}-only"
        write_package(tmp_path / effect, manifest)
        result = harness.registry.install(harness.operator, tmp_path / effect, source="file:///s",
                                          fixture_handler="calendar-write", enable_fixture=True)
        assert (result["status"], result["error"]["code"], result["error"]["message"]) == (
            "DENIED", "FORBIDDEN", "EFFECT_ABOVE_CEILING")
        assert result["data"]["lifecycle"] == "DRAFT"
        turn = harness.turn()
        described = turn.describe(turn.context, manifest["id"])
        assert (described.code, described.reason) == ("NOT_FOUND", "NOT_A_CAPABILITY_ID")
    assert harness.registry.records(harness.operator, enabled_only=True) == []


def test_registry_cas_tenant_and_lock(tmp_path: Path) -> None:
    harness = build(tmp_path)
    harness.install("calendar-read", enable=False)
    ref = "fixtures.calendar-read@1.0.0"
    record = harness.registry.record(harness.operator, ref)
    with pytest.raises(Refusal) as stale:
        harness.registry.transition(harness.operator, ref, record["revision"] - 1, "ENABLED",
                                    approval=harness.registry.fixture_enable_approval(harness.operator, ref))
    assert (stale.value.status, stale.value.reason) == ("CONFLICT", "REVISION_CONFLICT")
    other = context(tenant=OTHER_TENANT)
    with pytest.raises(Refusal) as foreign:
        harness.registry.record(other, ref)
    assert foreign.value.reason == "NOT_A_CAPABILITY_ID"
    lock = json.loads((harness.store.root / "capabilities.lock").read_text())
    assert lock["lock_version"] == 1
    entry = lock["entries"][0]
    assert set(entry) == {"id", "version", "sha256", "source", "installed_by_approval", "installed_at"}
    assert (entry["id"], entry["sha256"]) == ("fixtures.calendar-read", record["package_sha256"])
    history = json.loads((harness.store.root / "registry.json").read_text())["history"]
    assert [h["to"] for h in history] == ["DRAFT", "VALIDATED", "STAGED"]
    assert all("previous_revision" in h for h in history)
