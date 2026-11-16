"""REG-10 (RFC-015; M15-FR-03, M15-AT-02, M14-RT-02, K7): no manifest, no binding, no call.

S00 has no MCP transport; the discovery tool surface is the only model-facing gateway,
so the assertions are made on it.
"""

from __future__ import annotations

import json
from pathlib import Path

from s00_t03_support import build

from quati.application.discovery_tools import DISCOVERY_TOOLS, execute_tool_call
from quati.application.providers import ToolCall


def test_reg_10(tmp_path: Path) -> None:
    harness = build(tmp_path)
    harness.install("calendar-read")
    names = [tool.name for tool in DISCOVERY_TOOLS]
    assert names == ["quati_search", "quati_describe", "quati_invoke", "quati_status"]
    turn = harness.turn()
    text, step = execute_tool_call(turn, turn.context, ToolCall("quati_search", {"query": "read file contents"}))
    assert "read_file" not in text and "read_file" not in step["candidate_ids"]
    for tool_name in ("quati_describe", "quati_invoke"):
        arguments = {"capability_id": "read_file"} if tool_name == "quati_describe" else {
            "capability_id": "read_file", "input": {"path": "README.md"}}
        _text, step = execute_tool_call(turn, turn.context, ToolCall(tool_name, arguments))
        # Fix round 7 (LOG-0041 D4; M15 invoke guard order, "No existence oracle"): invoke of any id outside
        # the turn's shortlist was NOT_FOUND / NOT_A_CAPABILITY_ID for an unknown name; it is now the single
        # FORBIDDEN / NOT_IN_SHORTLIST. The registry lookup of describe is unchanged.
        expected = ("DENIED", "NOT_FOUND", "NOT_A_CAPABILITY_ID") if tool_name == "quati_describe" else (
            "DENIED", "FORBIDDEN", "NOT_IN_SHORTLIST")
        assert (step["status"], step["result_code"], step["reason"]) == expected
    _text, step = execute_tool_call(turn, turn.context, ToolCall("read_file", {"path": "README.md"}))
    assert (step["status"], step["reason"], step["operation"]) == ("BLOCKED", "TOOL_CALL_MALFORMED", "invalid")
    # Negative: a manifest-bound capability is visible and callable within policy.
    turn = harness.turn()
    execute_tool_call(turn, turn.context, ToolCall("quati_search", {"query": "find my next appointment"}))
    text, step = execute_tool_call(turn, turn.context, ToolCall(
        "quati_invoke", {"capability_id": "fixtures.calendar-read", "input": {"limit": 1}}))
    assert (step["status"], step["handler_executed"]) == ("SUCCEEDED", True)
    assert json.loads(text)["data"]["result_label"] == "FIXTURE_RESULT"
    # Fault: the binding is removed at runtime; the next call is refused.
    for binding_ref in harness.registry.binding_refs(harness.operator, "fixtures.calendar-read@1.0.0"):
        harness.registry.unbind(harness.operator, binding_ref)
    _text, step = execute_tool_call(turn, turn.context, ToolCall(
        "quati_invoke", {"capability_id": "fixtures.calendar-read", "input": {"limit": 2}}))
    assert (step["status"], step["reason"], step["handler_executed"]) == ("UNAVAILABLE", "NOT_ENABLED", False)
    assert harness.handlers.total_invocations() == 1
