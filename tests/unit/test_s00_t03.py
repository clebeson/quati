"""S00-T03 local assertions A01-A03 (WORK_PACKAGES.json), proof tier L1.

Each test drives the public application path (RegistryService install, DiscoveryTurn
and the model-facing discovery tool surface) over a temporary state directory.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest
from s00_t03_support import REPOSITORY_ROOT, build, write_package, manifest_copy

from quati.application.discovery_tools import execute_tool_call
from quati.application.providers import ToolCall
from quati.behavior.compiler import compile_documents
from quati.behavior.contracts import parse_yaml
from quati.domain.capability_registry import Refusal


def _root_prompt_hash() -> str:
    package = parse_yaml((REPOSITORY_ROOT / "examples/behavior/executive-secretary.yaml").read_bytes())
    package["statechart_ref"] = "statechart.yaml"
    machine = parse_yaml((REPOSITORY_ROOT / "examples/statecharts/commitment.yaml").read_bytes())
    return compile_documents(package, machine).receipt["prompt_hash"]


def _source_tree_hash() -> str:
    hasher = hashlib.sha256()
    for path in sorted((REPOSITORY_ROOT / "src/quati").rglob("*.py")):
        hasher.update(path.relative_to(REPOSITORY_ROOT).as_posix().encode() + b"\0" + path.read_bytes())
    return hasher.hexdigest()


def _search(turn, query: str) -> list[str]:
    result = turn.search(turn.context, query)
    assert result.status == "SUCCEEDED", result
    return [item["capability_id"] for item in result.data["candidates"]]


def test_a01(tmp_path: Path) -> None:
    """S00-T03-A01: a definition installed after startup is discoverable without root prompt edits."""
    prompt_before, code_before = _root_prompt_hash(), _source_tree_hash()
    harness = build(tmp_path)
    query = "expected weekly order volume for the north region next weeks"
    assert _search(harness.turn(), query) == []
    installed = harness.install("forecast-lime")
    assert installed["status"] == "SUCCEEDED"
    assert (installed["data"]["lifecycle"], installed["data"]["label"]) == ("ENABLED", "LOCAL_FIXTURE_ONLY")
    # Same running service: the next turn sees it; so does a restarted service.
    assert _search(harness.turn(), query) == ["fixtures.forecast-lime"]
    assert _search(harness.restart().turn(), query) == ["fixtures.forecast-lime"]
    assert (_root_prompt_hash(), _source_tree_hash()) == (prompt_before, code_before)


def test_a02(tmp_path: Path) -> None:
    """S00-T03-A02: manifests and packages cannot load code or grant permissions."""
    harness = build(tmp_path)
    marker = tmp_path / "executed.marker"
    manifest = manifest_copy("forecast-lime")
    manifest["id"] = "untrusted.forecast-copy"
    manifest["name"] = "forecast-copy"
    package = tmp_path / "pkg"
    write_package(package, manifest, extra_files={
        "scripts/payload.py": f"open({str(marker)!r}, 'w').write('ran')\n",
        "__init__.py": f"open({str(marker)!r}, 'w').write('ran')\n"})
    result = harness.registry.install(harness.operator, package, source="file:///synthetic/pkg")
    assert (result["status"], result["data"]["lifecycle"]) == ("SUCCEEDED", "VALIDATED")
    ref = result["data"]["definition_ref"]
    for implementation in ("python:payload", "file:scripts/payload.py", "module:scripts.payload:run",
                           "fixture:../scripts/payload", "fixture:calendar-read", "fixture:not-registered"):
        binding = harness.registry.fixture_binding(ref, "x")
        binding["implementation_ref"] = implementation
        with pytest.raises(Refusal) as refused_bind:
            harness.registry.bind(harness.operator, ref, binding)
        expected = "HANDLER_IDENTITY_MISMATCH" if implementation == "fixture:calendar-read" else "BINDING_CHECK_FAILED"
        assert refused_bind.value.reason == expected, implementation   # audit P1-1: trusted handler identity
    assert harness.registry.record(harness.operator, ref)["lifecycle"] == "VALIDATED"
    assert not marker.exists() and "payload" not in sys.modules
    assert harness.handlers.total_invocations() == 0
    # A manifest field cannot declare a handler or entry point.
    smuggled = manifest_copy("forecast-lime")
    smuggled["entry_point"] = "scripts.payload:run"
    write_package(tmp_path / "pkg2", smuggled)
    refused = harness.registry.install(harness.operator, tmp_path / "pkg2", source="file:///synthetic/pkg2")
    assert (refused["status"], refused["error"]["message"]) == ("BLOCKED", "MANIFEST_SCHEMA_INVALID")
    # Requested permissions are requirements, never grants: an ungranted permission hides the capability.
    greedy = manifest_copy("forecast-lime")
    greedy["id"], greedy["name"] = "untrusted.forecast-greedy", "forecast-greedy"
    greedy["permissions"] = ["forecast.read", "*", "admin"]
    write_package(tmp_path / "pkg3", greedy)
    harness.registry.install(harness.operator, tmp_path / "pkg3", source="file:///synthetic/pkg3",
                             fixture_handler="forecast-lime", enable_fixture=True)
    turn = harness.turn()
    assert "untrusted.forecast-greedy" not in _search(turn, "weekly order volume forecast north region")
    assert not marker.exists()


def test_a03(tmp_path: Path) -> None:
    """S00-T03-A03: denied, disabled and stale bindings never execute."""
    harness = build(tmp_path)
    for name in ("calendar-read", "calendar-write", "mail-search", "forecast-lime", "forecast-quick"):
        harness.install(name)
    turn = harness.turn()
    calls = [ToolCall("quati_search", {"query": "find my next appointment in my calendar"}),
             ToolCall("quati_search", {"query": "rough weekly order volume forecast region"})]
    for call in calls:
        execute_tool_call(turn, turn.context, call)
    # Denied: the write capability with read-only grants (never enabled, never shortlisted).
    _text, step = execute_tool_call(turn, turn.context, ToolCall(
        "quati_invoke", {"capability_id": "fixtures.calendar-write",
                         "input": {"title": "x", "start": "2026-11-17T09:00:00Z", "end": "2026-11-17T10:00:00Z"}}))
    assert (step["status"], step["reason"], step["handler_executed"]) == ("DENIED", "NOT_IN_SHORTLIST", False)
    # Disabled after it was shortlisted.
    assert "fixtures.forecast-quick" in turn.shortlist
    record = harness.registry.record(harness.operator, "fixtures.forecast-quick@1.0.0")
    harness.registry.transition(harness.operator, "fixtures.forecast-quick@1.0.0", record["revision"], "DISABLED")
    _text, step = execute_tool_call(turn, turn.context, ToolCall(
        "quati_invoke", {"capability_id": "fixtures.forecast-quick", "input": {"region": "north"}}))
    assert (step["status"], step["reason"], step["handler_executed"]) == ("UNAVAILABLE", "NOT_ENABLED", False)
    # Stale: the binding is replaced after the shortlist was built.
    assert "fixtures.forecast-lime" in turn.shortlist
    ref = "fixtures.forecast-lime@1.0.0"
    old = harness.registry.record(harness.operator, ref)
    for binding_ref in harness.registry.binding_refs(harness.operator, ref):
        harness.registry.unbind(harness.operator, binding_ref)
    harness.registry.bind(harness.operator, ref, harness.registry.fixture_binding(ref, "forecast-lime", suffix="b2"))
    assert harness.registry.record(harness.operator, ref)["lifecycle"] == "VALIDATED"
    assert old["assurance"] == "C2" and harness.registry.record(harness.operator, ref)["assurance"] == "C0"
    _text, step = execute_tool_call(turn, turn.context, ToolCall(
        "quati_invoke", {"capability_id": "fixtures.forecast-lime", "input": {"region": "north", "horizon_weeks": 2}}))
    assert (step["status"], step["reason"], step["handler_executed"]) == ("UNAVAILABLE", "NOT_ENABLED", False)
    # Stale package bytes: one byte changed after the shortlist was built.
    package_file = harness.store.package_dir("fixtures.calendar-read", "1.0.0") / "capability.scs.json"
    package_file.write_bytes(package_file.read_bytes().replace(b"appointments", b"appointmentz", 1))
    _text, step = execute_tool_call(turn, turn.context, ToolCall(
        "quati_invoke", {"capability_id": "fixtures.calendar-read", "input": {"limit": 1}}))
    assert (step["status"], step["reason"], step["handler_executed"]) == ("UNAVAILABLE", "DIGEST_MISMATCH", False)
    assert harness.handlers.total_invocations() == 0
    assert json.loads(_text)["status"] == "UNAVAILABLE"
