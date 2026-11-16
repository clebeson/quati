"""REG-03 (RFC-015; M14-FR-02, M14-RT-02, M15-RT-02, K7): MCP hints are stored, never trusted."""

from __future__ import annotations

from pathlib import Path

import pytest

from s00_t03_support import AGENT, build, context

from quati.domain.capability_registry import Refusal

TOOL = {
    "name": "read_file",
    "description": "Read one file from the synthetic project workspace and return its text content.",
    "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
    "annotations": {"readOnlyHint": True},
}
INTENTS = {"positive_examples": ["Read the README file", "Show me the contents of notes.txt"],
           "negative_examples": ["Delete the README file"]}


def _import(harness, tool=TOOL):
    return harness.registry.import_mcp_tool(harness.operator, tool, server="io.example.files",
                                            server_version="1.2.0", intents=INTENTS,
                                            quarantine=harness.root / "quarantine")


def test_reg_03(tmp_path: Path) -> None:
    harness = build(tmp_path)
    result = _import(harness)
    assert (result["status"], result["error"]["message"]) == ("DENIED", "EFFECT_ABOVE_CEILING")
    ref = result["data"]["definition_ref"]
    record = harness.registry.record(harness.operator, ref)
    assert record["capability_id"] == "io.example.files.read_file"
    assert record["import_kind"] == "mcp_tool" and record["lifecycle"] == "DRAFT"
    assert record["effect_class_reviewed"] is None
    assert record["vendor_hints"] == {"mcp_annotations": {"readOnlyHint": True}}
    assert harness.registry.manifest(harness.operator, ref)["effects"] == "dangerous"
    assert harness.registry.effective_effect(harness.operator, ref) == "dangerous"
    # Fault: re-import does not downgrade silently.
    again = _import(harness)
    assert again["data"]["lifecycle"] == "DRAFT"
    assert harness.registry.record(harness.operator, ref) == record
    changed = dict(TOOL, annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True})
    conflict = _import(harness, changed)
    assert (conflict["status"], conflict["error"]["message"]) == ("CONFLICT", "VERSION_EXISTS")
    assert harness.registry.record(harness.operator, ref) == record
    assert harness.turn().search(harness.operator, "read the readme file").data["candidates"] == []


def test_reg_03_review_only_through_human_approval(tmp_path: Path) -> None:
    harness = build(tmp_path)
    ref = _import(harness)["data"]["definition_ref"]
    record = harness.registry.record(harness.operator, ref)
    agent = context(actor=AGENT, kind="AGENT")
    with pytest.raises(Refusal) as refused:
        harness.registry.review_effect_class(agent, ref, record["revision"], "read", approval=None)
    assert refused.value.reason == "REVIEW_REQUIRES_HUMAN_APPROVAL"
    with pytest.raises(Refusal):
        harness.registry.review_approval(agent, ref, "read")
    approval = harness.registry.review_approval(harness.operator, ref, "read")
    with pytest.raises(Refusal) as refused:
        harness.registry.review_effect_class(agent, ref, record["revision"], "read", approval=approval)
    assert refused.value.reason == "REVIEW_REQUIRES_HUMAN_APPROVAL"
    assert harness.registry.record(harness.operator, ref) == record
    reviewed = harness.registry.review_effect_class(harness.operator, ref, record["revision"], "read",
                                                    approval=approval)
    assert (reviewed["effect_class_reviewed"], reviewed["revision"]) == ("read", record["revision"] + 1)
    assert reviewed["vendor_hints"] == record["vendor_hints"] and reviewed["lifecycle"] == "DRAFT"
    with pytest.raises(Refusal) as reused:
        harness.registry.review_effect_class(harness.operator, ref, reviewed["revision"], "none", approval=approval)
    assert reused.value.reason == "REVIEW_REQUIRES_HUMAN_APPROVAL"
