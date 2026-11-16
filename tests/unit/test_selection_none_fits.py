"""REG-08 (RFC-015; M15-FR-02, M15-FR-03, M15-AT-02): honest no-capability path, scripted model only."""

from __future__ import annotations

import json
from pathlib import Path

from s00_t03_support import build

from quati.application.discovery_tools import execute_tool_call, honest_no_capability
from quati.application.providers import ToolCall
from quati.domain.discovery import resolve_choice


def test_reg_08(tmp_path: Path) -> None:
    harness = build(tmp_path)
    turn = harness.turn()
    text, step = execute_tool_call(turn, turn.context, ToolCall("quati_search", {"query": "find my next appointment"}))
    result = json.loads(text)
    assert result["data"]["candidates"] == [] and step["candidate_ids"] == []
    assert result["uncertainties"] == ["NO_CANDIDATES"] and result["next_action"] == "report_no_capability"
    assert resolve_choice({"capability_id": "fixtures.calendar-read", "arguments": {}}, ()).verdict == "NO_CAPABILITY"
    # A NONE_FITS reply from a scripted model after a non-empty search.
    harness.install("mail-search")
    turn = harness.turn()
    execute_tool_call(turn, turn.context, ToolCall("quati_search", {"query": "search my email messages"}))
    assert list(turn.shortlist) == ["fixtures.mail-search"]
    text, step = execute_tool_call(turn, turn.context,
                                   ToolCall("quati_invoke", {"capability_id": "NONE_FITS", "input": {}}))
    assert (step["status"], step["operation"], step["handler_executed"]) == ("SUCCEEDED", "none_fits", False)
    assert json.loads(text)["next_action"] == "report_no_capability"
    assert resolve_choice({"capability_id": "NONE_FITS", "arguments": {}}, tuple(turn.shortlist)).verdict == (
        "NO_CAPABILITY")
    assert harness.handlers.total_invocations() == 0
    # Fault: a model timeout yields the same honest response.
    timeout = honest_no_capability("MODEL_TIMEOUT")
    assert timeout["status"] == "SUCCEEDED" and timeout["next_action"] == "report_no_capability"
    assert timeout["data"] == {"outcome": "NO_CAPABILITY", "reason": "MODEL_TIMEOUT"}
    # Negative: a fitting shortlisted item is selected and runs.
    choice = resolve_choice({"capability_id": "fixtures.mail-search", "arguments": {"query": "invoice"}},
                            tuple(turn.shortlist))
    assert (choice.verdict, choice.capability_id) == ("SELECTED", "fixtures.mail-search")
    text, step = execute_tool_call(turn, turn.context, ToolCall(
        "quati_invoke", {"capability_id": choice.capability_id, "input": choice.arguments}))
    assert (step["status"], step["handler_executed"]) == ("SUCCEEDED", True)
    assert json.loads(text)["data"]["result_label"] == "FIXTURE_RESULT"
