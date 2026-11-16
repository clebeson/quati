"""REG-01 (RFC-015; M14-FR-01, M14-RT-01, K7), contribution at L1 through RegistryService.install."""

from __future__ import annotations

import shutil
from pathlib import Path

from s00_t03_support import REPOSITORY_ROOT, build, manifest_copy, write_package

from quati.application.capability_registry import RegistryService
from quati.behavior.contracts import ContractCatalog


def test_reg_01(tmp_path: Path) -> None:
    harness = build(tmp_path)
    for field, value in (("lifecycle", "enabled"), ("assurance", "C5"), ("enabled", True)):
        manifest = manifest_copy("forecast-lime")
        manifest[field] = value
        write_package(tmp_path / field, manifest)
        result = harness.registry.install(harness.operator, tmp_path / field, source="file:///synthetic",
                                          fixture_handler="forecast-lime", enable_fixture=True)
        assert (result["status"], result["error"]["code"], result["error"]["message"]) == (
            "BLOCKED", "INVALID_INPUT", "MANIFEST_SCHEMA_INVALID"), field
    assert harness.registry.records(harness.operator) == []
    assert harness.turn().search(harness.operator, "weekly order volume forecast").data["candidates"] == []
    # Negative: the same manifest without those fields is accepted.
    write_package(tmp_path / "clean", manifest_copy("forecast-lime"))
    accepted = harness.registry.install(harness.operator, tmp_path / "clean", source="file:///synthetic",
                                        fixture_handler="forecast-lime", enable_fixture=True)
    assert (accepted["status"], accepted["data"]["lifecycle"]) == ("SUCCEEDED", "ENABLED")


def test_reg_01_fault_corrupt_schema_fails_closed(tmp_path: Path) -> None:
    contracts = tmp_path / "contracts"
    shutil.copytree(REPOSITORY_ROOT / "contracts", contracts)
    (contracts / "scs-capability.schema.json").write_text('{"type": "object", "properties": ')
    harness = build(tmp_path)
    broken = RegistryService(harness.store, harness.handlers, clock=harness.clock, ids=harness.ids,
                             catalog=ContractCatalog(contracts))
    write_package(tmp_path / "pkg", manifest_copy("forecast-lime"))
    result = broken.install(harness.operator, tmp_path / "pkg", source="file:///synthetic",
                            fixture_handler="forecast-lime", enable_fixture=True)
    assert result["status"] == "BLOCKED"
    assert (result["error"]["code"], result["error"]["message"]) == ("CONFIG_INVALID", "SCHEMA_UNAVAILABLE")
    assert broken.records(harness.operator) == []
