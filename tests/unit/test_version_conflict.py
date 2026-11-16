"""REG-06 (RFC-015; M14-FR-01, M14-RT-01, K7): same id and version is never silently replaced."""

from __future__ import annotations

from pathlib import Path

import pytest

from s00_t03_support import build, manifest_copy, write_package


def _install(harness, name: str, manifest: dict):
    write_package(harness.root / name, manifest)
    return harness.registry.install(harness.operator, harness.root / name, source=f"file:///synthetic/{name}",
                                    fixture_handler="forecast-lime", enable_fixture=True)


def _candidates(turn):
    result = turn.search(turn.context, "weekly order volume forecast north region")
    return [(item["capability_id"], item["capability_version"]) for item in result.data["candidates"]]


def test_reg_06(tmp_path: Path) -> None:
    harness = build(tmp_path)
    harness.install("forecast-lime")
    original = harness.registry.record(harness.operator, "fixtures.forecast-lime@1.0.0")
    same_version = manifest_copy("forecast-lime")
    same_version["description"] += " Revised wording."
    conflict = _install(harness, "same-version", same_version)
    assert (conflict["status"], conflict["error"]["code"], conflict["error"]["message"]) == (
        "CONFLICT", "REVISION_CONFLICT", "VERSION_EXISTS")
    assert harness.registry.record(harness.operator, "fixtures.forecast-lime@1.0.0") == original
    major = manifest_copy("forecast-lime")
    major["version"] = "2.0.0"
    major["input_schema"]["properties"]["horizon_weeks"]["maximum"] = 8
    assert _install(harness, "major", major)["data"]["lifecycle"] == "ENABLED"
    versions = sorted(record["capability_version"] for record in harness.registry.records(harness.operator))
    assert versions == ["1.0.0", "2.0.0"]
    assert harness.registry.record(harness.operator, "fixtures.forecast-lime@1.0.0") == original
    # Negative: a compatible version with a new digest is a new entry.
    minor = manifest_copy("forecast-lime")
    minor["version"] = "1.1.0"
    assert _install(harness, "minor", minor)["status"] == "SUCCEEDED"
    versions = sorted(record["capability_version"] for record in harness.registry.records(harness.operator))
    assert versions == ["1.0.0", "1.1.0", "2.0.0"]
    assert _candidates(harness.turn()) == [("fixtures.forecast-lime", "2.0.0")]


def test_reg_06_fault_interrupted_second_install(tmp_path: Path) -> None:
    harness = build(tmp_path)
    harness.install("forecast-lime")
    original = harness.registry.record(harness.operator, "fixtures.forecast-lime@1.0.0")

    def crash(point: str) -> None:
        if point == "registry.before_rename":
            raise RuntimeError("injected crash")

    harness.store.hook = crash
    second = manifest_copy("forecast-lime")
    second["version"] = "1.1.0"
    with pytest.raises(RuntimeError):
        _install(harness, "second", second)
    restarted = harness.restart()
    assert restarted.registry.record(restarted.operator, "fixtures.forecast-lime@1.0.0") == original
    assert _candidates(restarted.turn()) == [("fixtures.forecast-lime", "1.0.0")]
