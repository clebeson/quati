"""REG-09 (RFC-015; M15-FR-03, M15-RT-02, M15-AT-02): an out-of-shortlist choice is a selection error."""

from __future__ import annotations

from pathlib import Path

from s00_t03_support import build

from quati.application.discovery_tools import execute_tool_call
from quati.application.providers import ToolCall


def test_reg_09(tmp_path: Path) -> None:
    harness = build(tmp_path)
    for name in ("calendar-read", "mail-search", "forecast-lime"):
        harness.install(name)
    turn = harness.turn()
    execute_tool_call(turn, turn.context, ToolCall("quati_search", {"query": "find my next appointment"}))
    assert "fixtures.forecast-lime" not in turn.shortlist
    _text, step = execute_tool_call(turn, turn.context, ToolCall(
        "quati_invoke", {"capability_id": "fixtures.forecast-lime", "input": {"region": "north", "horizon_weeks": 1}}))
    assert (step["status"], step["result_code"], step["reason"]) == ("DENIED", "FORBIDDEN", "NOT_IN_SHORTLIST")
    assert step["selection_error"] is True and step["handler_executed"] is False
    errors = [e for e in harness.store.audit_events() if e["event"] == "discovery.selection_error"]
    assert errors and errors[-1]["capability_id"] == "fixtures.forecast-lime"
    # Fault: malformed id strings are rejected without side effect.
    for bad in ("", "FIXTURES.CALENDAR-READ", "../../etc/passwd", "fixtures.calendar-read@1.0.0", "x" * 300):
        turn = harness.turn()
        _text, step = execute_tool_call(turn, turn.context,
                                        ToolCall("quati_invoke", {"capability_id": bad, "input": {}}))
        assert step["status"] in ("DENIED", "BLOCKED") and step["handler_executed"] is False, bad
    _text, step = execute_tool_call(turn, turn.context, ToolCall("quati_invoke", {"capability_id": 42, "input": {}}))
    assert step["reason"] == "TOOL_CALL_MALFORMED"
    assert harness.handlers.total_invocations() == 0
    # Negative: an in-shortlist id passes validation.
    turn = harness.turn()
    execute_tool_call(turn, turn.context, ToolCall("quati_search", {"query": "find my next appointment"}))
    _text, step = execute_tool_call(turn, turn.context, ToolCall(
        "quati_invoke", {"capability_id": "fixtures.calendar-read", "input": {"limit": 1}}))
    assert (step["status"], step["selection_error"], step["handler_executed"]) == ("SUCCEEDED", False, True)
