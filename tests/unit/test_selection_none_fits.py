"""REG-08 (RFC-015; M15-FR-02, M15-FR-03, M15-AT-02): honest no-capability path, scripted model only."""

from __future__ import annotations

import json
from pathlib import Path

from s00_t03_support import build
from s00_t04_support import Harness, Script, classified, search

from quati.application.discovery_tools import execute_tool_call
from quati.application.providers import ProviderError, ToolCall
from quati.domain.discovery import resolve_choice


def test_reg_08(tmp_path: Path, monkeypatch) -> None:
    harness = build(tmp_path / "registry")
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
    # Fault: the model times out after its search. Integration step 8 (LOG-0044 decision D7): the fault step
    # was `honest_no_capability("MODEL_TIMEOUT")`, a helper no product path called, asserted to be SUCCEEDED with
    # outcome NO_CAPABILITY. The honest answer is now observed on the ask path itself: a typed non-success
    # (DEADLINE_EXCEEDED, exit 5), nothing invoked, no work claimed.
    script = Script(classified(), search("search my email messages"), ProviderError("DEADLINE_EXCEEDED"))
    asking = Harness(tmp_path / "ask", monkeypatch, script)
    asking.install("mail-search")
    assert asking.probe()[0] == 0
    code, value = asking.ask("Search my email messages for the invoice")
    assert (code, value["status"], value["error"]["code"]) == (5, "BLOCKED", "DEADLINE_EXCEEDED")
    assert (value["data"]["result_kind"], value["data"]["launched"]) == ("BLOCKED", False)
    assert value["data"].get("work_performed") is not True and "fixture_results" not in value["data"]
    assert [step["handler_executed"] for step in value["data"]["tool_calls"]] == [False]
    assert asking.handlers.total_invocations() == 0
    # Negative: a fitting shortlisted item is selected and runs.
    choice = resolve_choice({"capability_id": "fixtures.mail-search", "arguments": {"query": "invoice"}},
                            tuple(turn.shortlist))
    assert (choice.verdict, choice.capability_id) == ("SELECTED", "fixtures.mail-search")
    text, step = execute_tool_call(turn, turn.context, ToolCall(
        "quati_invoke", {"capability_id": choice.capability_id, "input": choice.arguments}))
    assert (step["status"], step["handler_executed"]) == ("SUCCEEDED", True)
    assert json.loads(text)["data"]["result_label"] == "FIXTURE_RESULT"
