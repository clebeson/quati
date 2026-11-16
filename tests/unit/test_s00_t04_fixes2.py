"""S00-T04 fix round 2, after the claude_cli haiku gate run T05-20261116T071601Z-claude_cli-haiku-gate1.

Each test names the finding it discriminates (R1 false "tools unavailable", R2 social
over-correction, R3 probe flake, R4 describe before invoke, R5 synthetic-evidence prompts).
Proof tier L1: a SCRIPTED FAKE model (tests/unit/s00_t04_support.py) or a scripted
child-process runner. No network, no real provider and no ``QUATI_ALLOW_LIVE``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from s00_t04_support import (  # noqa: E402
    CALENDAR_QUERY, SOCIAL, WORK, Harness, Script, classified, describe, final, invoke, receipt_bytes, receipt_of,
    search)
from quati.application import ask as ask_module  # noqa: E402
from quati.application.discovery_tools import DISCOVERY_TOOLS  # noqa: E402
from quati.application.providers import Message, ModelRequest, ToolSpec  # noqa: E402


def ready(tmp_path, monkeypatch, *items, fixtures=("calendar-read", "calendar-write", "mail-search"), **options):
    script = Script(*items)
    harness = Harness(tmp_path, monkeypatch, script, **options)
    harness.install(*fixtures)
    assert harness.probe()[0] == 0
    harness.base = len(script.requests)
    return harness


def model_requests(harness):
    return harness.script.requests[harness.base:]


def read_flow():
    return (search(CALENDAR_QUERY), describe("fixtures.calendar-read"), invoke("fixtures.calendar-read", limit=1))


# --------------------------------------------------------------- R1 false "tools unavailable"
def test_r1_cli_tool_instructions_say_the_tools_are_available():
    from quati.adapters.providers.cli import ClaudeCliProvider
    from test_provider_adapters import Runner, claude_result, make_cli
    envelope = {"kind": "final", "tool_name": "", "arguments_json": "", "text": "ok"}
    runner = Runner(claude_result(structured_output=envelope))
    provider = make_cli(ClaudeCliProvider, runner)
    tool = ToolSpec("quati_search", "Search.", {"type": "object", "properties": {"query": {"type": "string"}}})
    provider.complete(ModelRequest((Message("user", "Do I have anything booked soon?"),), system="S.",
                                   tools=(tool,)))
    system = runner.calls[0]["system"]
    assert "cannot run tools" not in system.lower()
    assert "Quati runs the tools listed below on your behalf" in system
    assert "available in this conversation" in system
    assert "in the language of the user's request" in system


def test_r1_protocol_says_reply_in_the_language_of_the_request(tmp_path, monkeypatch):
    harness = ready(tmp_path, monkeypatch, classified(), *read_flow(), final())
    harness.ask(CALENDAR_QUERY)
    for request in model_requests(harness)[1:]:
        assert "Reply in the language of the user's request" in request.system


def test_r1_work_request_with_zero_tool_calls_gets_one_continuation(tmp_path, monkeypatch):
    harness = ready(tmp_path, monkeypatch, classified(),
                    final("Je ne peux pas: l'outil de recherche n'est pas disponible."), *read_flow(), final("ok"))
    code, value = harness.ask(CALENDAR_QUERY, synthetic=True)
    assert (code, value["data"]["result_kind"]) == (0, "FIXTURE_RESULT")
    assert model_requests(harness)[2].messages[-1].content == ask_module.SEARCH_CONTINUATION_TEXT
    evidence = receipt_of(value)["synthetic_evidence"]
    assert evidence["continuations"] == [{"after_step": 0, "reason": "NO_SEARCH_ON_WORK"}]


def test_r1_non_social_classification_without_work_flag_also_continues(tmp_path, monkeypatch):
    answer = dict(WORK, intent="simple_answer", work_needed=False, next_action="respond")
    harness = ready(tmp_path, monkeypatch, classified(answer), final("A semaphore limits concurrency."),
                    final("Still an answer."))
    code, value = harness.ask("What does a semaphore do?")
    assert len(model_requests(harness)) == 3 and value["data"]["reason"] == "NO_VERIFIED_EXECUTION"


def test_r1_at_most_one_continuation_per_ask(tmp_path, monkeypatch):
    harness = ready(tmp_path, monkeypatch, classified(), final("tools unavailable"), search(CALENDAR_QUERY),
                    final("Checking..."), final("never requested"))
    code, value = harness.ask(CALENDAR_QUERY)
    assert (value["status"], value["error"]["code"]) == ("BLOCKED", "EVIDENCE_INSUFFICIENT")
    assert len(model_requests(harness)) == 4 and len(harness.script.items) == 1
    assert receipt_of(value)["continuations"] == [{"after_step": 0, "reason": "NO_SEARCH_ON_WORK"}]


# --------------------------------------------------------------- R2 social conversation
# Fix round 3 P1-C (root decision, recorded change): the texts below are not social vocabulary only, so a
# CONVERSATION now also needs the model to keep making zero tool calls after the one NO_SEARCH_ON_WORK
# continuation. Each script gained that first tool-free reply, and the request count moved from 2 to 3.
# Fix round 7 (LOG-0041 D2 and N17; S00_RUNTIME_CONTRACT "Displayed text and social outcomes" rule 3): the
# three tests below changed expectation and were renamed. Old: a social label on a text that opens with a
# greeting ended CONVERSATION / SUCCEEDED exit 0 with the greeting template (and an empty model reply was
# BLOCKED EMPTY_SOCIAL_REPLY). New: the text is not social-only by the table, so the label ends BLOCKED /
# EVIDENCE_INSUFFICIENT / NO_VERIFIED_EXECUTION exit 4; the model text is never displayed and its content,
# empty or not, changes nothing.
def test_r2_social_classification_and_tool_free_loop_is_blocked_not_a_conversation(tmp_path, monkeypatch):
    harness = ready(tmp_path, monkeypatch, classified(SOCIAL), final("Hi!"),
                    final("  Hello,   thanks for asking!\n How can I help? "))
    code, value = harness.ask("Hey there! Hope your day is going well.")
    data = value["data"]
    assert (code, value["status"], data["result_kind"]) == (4, "BLOCKED", "BLOCKED")
    assert (value["error"]["code"], data["reason"]) == ("EVIDENCE_INSUFFICIENT", "NO_VERIFIED_EXECUTION")
    assert "text" not in data and "text_source" not in data and "thanks for asking" not in json.dumps(value)
    assert value["uncertainties"] == ["NO_VERIFIED_EXECUTION"]
    assert value["next_action"] == ask_module.MODEL_ANSWER_NEXT_ACTION
    assert (data["commitment_id"], data["delivered"], data["tool_calls"]) == (None, False, [])
    assert len(model_requests(harness)) == 3                                   # P1-C: one continuation (was 2)
    assert receipt_of(value)["continuations"] == [{"after_step": 0, "reason": "NO_SEARCH_ON_WORK"}]
    assert harness.handlers.total_invocations() == 0
    assert receipt_of(value)["outcome"]["result_kind"] == "BLOCKED"


def test_r2_model_text_is_never_displayed_and_an_empty_reply_is_not_a_failure_mode(tmp_path, monkeypatch):
    harness = ready(tmp_path, monkeypatch, classified(SOCIAL), final("Hi!"), final("word " * 200))
    code, value = harness.ask("Good morning! Urgent: just wanted to say hi.")
    assert (code, value["data"]["result_kind"], value["data"]["reason"]) == (4, "BLOCKED", "NO_VERIFIED_EXECUTION")
    assert "text" not in value["data"] and "word word" not in json.dumps(value)
    empty = ready(tmp_path / "e", monkeypatch, classified(SOCIAL), final("Hi!"), final("   "))
    code, value = empty.ask("Good morning! Urgent: just wanted to say hi.")
    assert (code, value["status"], value["error"]["code"], value["data"]["reason"]) == (
        4, "BLOCKED", "EVIDENCE_INSUFFICIENT", "NO_VERIFIED_EXECUTION")


def test_r2_both_signals_must_agree(tmp_path, monkeypatch):
    # Social label but the loop used a tool: not a conversation (the shortlist continuation applies).
    harness = ready(tmp_path, monkeypatch, classified(SOCIAL), search(CALENDAR_QUERY), final("Hi!"), final("Hi!"))
    code, value = harness.ask("Hey there, any appointment soon?")
    assert value["data"]["result_kind"] == "BLOCKED" and value["status"] == "BLOCKED"
    # Work label and a tool-free loop, even after the continuation: stays BLOCKED.
    work = ready(tmp_path / "w", monkeypatch, classified(), final("Hello!"), final("Hello again!"))
    code, value = work.ask("Hello, find my next appointment")
    assert (value["status"], value["data"]["result_kind"]) == ("BLOCKED", "BLOCKED") and code == 4


def test_r2_result_kinds_have_no_conversation():
    assert "CONVERSATION" not in ask_module.RESULT_KINDS
    assert "CONVERSATION" not in ask_module.__doc__


# --------------------------------------------------------------- R3 probe verdicts
def test_r3_probe_retries_a_transient_tool_miss_once_and_records_it(tmp_path, monkeypatch):
    script = Script(probe_tools="flaky")
    harness = Harness(tmp_path, monkeypatch, script)
    code, value = harness.probe()
    report = value["data"]["feature_report"]
    assert (code, value["status"], report["features"]["tools"]) == (0, "SUCCEEDED", "SUPPORTED")
    assert report["attempts"]["tools"] == 2 and report["retried"] == {"tools": "CLI_FAILED"}
    # Fix round 4 (G2) added the typed ``detail`` key to every verdict (None when SUPPORTED); expectation updated.
    assert value["data"]["verdicts"]["tools"] == {"verdict": "SUPPORTED", "reason": "PROBE_PASSED", "attempts": 2,
                                                  "detail": None}
    assert len([request for request in script.requests if request.tools]) == 2


def test_r3_probe_with_unverified_tools_is_partial_not_succeeded(tmp_path, monkeypatch):
    script = Script(probe_tools="fail")
    harness = Harness(tmp_path, monkeypatch, script)
    code, value = harness.probe()
    assert (code, value["status"]) == (0, "PARTIAL")
    assert value["data"]["verdicts"]["tools"] == {"verdict": "NOT_VERIFIED", "reason": "UPSTREAM_ERROR",
                                                  "attempts": 2,
                                                  # Fix round 4 (G2): typed detail added; expectation updated.
                                                  "detail": "TRANSPORT_ERROR:TEMPORARILY_UNAVAILABLE:UPSTREAM_ERROR"}
    assert "TOOLS_NOT_VERIFIED:UPSTREAM_ERROR" in value["uncertainties"]
    assert "probe again" in value["next_action"]
    assert len([request for request in script.requests if request.tools]) == 2       # bounded: one retry


def test_r3_wrong_nonce_is_a_measurement_and_is_not_retried(tmp_path, monkeypatch):
    script = Script(probe_tools="wrong")
    harness = Harness(tmp_path, monkeypatch, script)
    code, value = harness.probe()
    assert (code, value["status"], value["data"]["verdicts"]["tools"]["attempts"]) == (0, "PARTIAL", 1)
    assert "TOOLS_UNSUPPORTED:NONCE_MISMATCH" in value["uncertainties"]


def test_r3_probe_without_an_observed_model_id_is_partial(tmp_path, monkeypatch):
    harness = Harness(tmp_path, monkeypatch, Script(probe_model_id=""))
    code, value = harness.probe()
    assert (code, value["status"]) == (0, "PARTIAL") and "MODEL_ID_UNOBSERVED" in value["uncertainties"]


def test_r3_fully_supported_probe_stays_succeeded(tmp_path, monkeypatch):
    harness = Harness(tmp_path, monkeypatch, Script())
    code, value = harness.probe()
    assert (code, value["status"]) == (0, "SUCCEEDED")
    assert value["data"]["verdicts"]["structured_output"]["verdict"] == "SUPPORTED"


# --------------------------------------------------------------- R4 describe before invoke
def test_r4_invoke_without_describe_is_refused_and_the_model_can_recover(tmp_path, monkeypatch):
    harness = ready(tmp_path, monkeypatch, classified(), search(CALENDAR_QUERY),
                    invoke("fixtures.calendar-read", limit=1), describe("fixtures.calendar-read"),
                    invoke("fixtures.calendar-read", limit=1), final("ok"))
    code, value = harness.ask(CALENDAR_QUERY)
    assert (code, value["status"]) == (0, "SUCCEEDED")
    steps = value["data"]["tool_calls"]
    assert [(step["operation"], step["reason"]) for step in steps] == [
        ("search", None), ("invoke", "DESCRIBE_REQUIRED"), ("describe", None), ("invoke", None)]
    told = model_requests(harness)[3].messages[-1].content
    assert "DESCRIBE_REQUIRED" in told and "quati_describe" in told
    assert harness.handlers.invocations() == {"calendar-read": 1}


def test_r4_describe_required_after_a_success_does_not_make_it_partial(tmp_path, monkeypatch):
    harness = ready(tmp_path, monkeypatch, classified(), search(CALENDAR_QUERY), search("search mail messages"),
                    describe("fixtures.calendar-read"), invoke("fixtures.calendar-read", limit=1),
                    invoke("fixtures.mail-search", query="x"), final("ok"))
    code, value = harness.ask(CALENDAR_QUERY)
    assert value["data"]["tool_calls"][-1]["reason"] == "DESCRIBE_REQUIRED"
    assert (code, value["status"]) == (0, "SUCCEEDED")


def test_r4_describe_required_ranks_after_the_real_guards(tmp_path, monkeypatch):
    harness = ready(tmp_path, monkeypatch, classified(), invoke("fixtures.calendar-read", limit=1),
                    final("x"), final("x"))
    code, value = harness.ask(CALENDAR_QUERY)
    assert value["data"]["tool_calls"][0]["reason"] == "NOT_IN_SHORTLIST"
    # A shortlisted id refused by a real guard (guard 4, lifecycle) keeps that reason: DESCRIBE_REQUIRED
    # is checked only after guards 4-6, so it never masks them.
    from quati.application.discovery_tools import execute_tool_call
    from quati.application.providers import ToolCall
    context = harness.identity.authenticate()
    turn = harness.runtime(context).discovery.begin_turn(context, require_describe=True)
    turn.shortlist["fixtures.calendar-read"] = "9.9.9"                     # a version that is not ENABLED
    _text, step = execute_tool_call(turn, context, ToolCall("quati_invoke", {
        "capability_id": "fixtures.calendar-read", "input": {"limit": 1}}))
    assert step["reason"] == "NOT_ENABLED"
    turn.shortlist["fixtures.calendar-read"] = "1.0.0"
    _text, step = execute_tool_call(turn, context, ToolCall("quati_invoke", {
        "capability_id": "fixtures.calendar-read", "input": {"bad": True}}))
    assert step["reason"] == "DESCRIBE_REQUIRED"                          # before argument validation (guard 7)


def test_r4_tool_descriptions_require_describe_first():
    tools = {tool.name: tool.description for tool in DISCOVERY_TOOLS}
    assert "before quati_invoke" in tools["quati_describe"]
    assert "described with quati_describe in this turn" in tools["quati_invoke"]


def test_r4_the_t03_turn_api_keeps_its_default(tmp_path, monkeypatch):
    harness = ready(tmp_path, monkeypatch)
    context = harness.identity.authenticate()
    turn = harness.runtime(context).discovery.begin_turn(context)
    assert turn.require_describe is False


# --------------------------------------------------------------- R5 model-visible text in synthetic evidence
def test_r5_synthetic_evidence_records_the_exact_model_visible_text(tmp_path, monkeypatch):
    harness = ready(tmp_path, monkeypatch, classified(), *read_flow(), final("ok"))
    code, value = harness.ask(CALENDAR_QUERY + " private-marker-5521", synthetic=True)
    calls = receipt_of(value)["synthetic_evidence"]["model_calls"]
    for call, request in zip(calls, model_requests(harness)):
        visible = call["model_visible"]
        assert visible["system"] == request.system
        assert visible["messages"] == [{"role": m.role, "content": m.content} for m in request.messages]
        assert visible["tool_names"] == [tool.name for tool in request.tools]
        assert len(visible["sha256"]) == 64
    plain = ready(tmp_path / "p", monkeypatch, classified(), *read_flow(), final("ok"))
    code, value = plain.ask(CALENDAR_QUERY + " private-marker-5521")
    raw = receipt_bytes(value)
    assert b"private-marker-5521" not in raw and b"Protected Quati invariants" not in raw
    assert b"model_visible" not in raw


def test_r5_cli_transport_reports_its_exact_rendering():
    from quati.adapters.providers.cli import ClaudeCliProvider, CodexCliProvider
    from test_provider_adapters import Runner, claude_result, make_cli
    envelope = {"kind": "final", "tool_name": "", "arguments_json": "", "text": "ok"}
    runner = Runner(claude_result(structured_output=envelope))
    provider = make_cli(ClaudeCliProvider, runner)
    tool = ToolSpec("quati_search", "Search.", {"type": "object", "properties": {"query": {"type": "string"}}})
    request = ModelRequest((Message("user", "first"), Message("assistant", "a"), Message("user", "second")),
                           system="S.", tools=(tool,))
    provider.complete(request)
    visible = provider.model_visible(request)
    assert visible["system"] == runner.calls[0]["system"] and visible["stdin"] == runner.calls[0]["stdin"]
    codex = make_cli(CodexCliProvider, Runner())
    rendered = codex.model_visible(ModelRequest((Message("user", "hello"),), system="Be brief."))
    assert rendered == {"system": "Be brief.", "stdin": "Be brief.\n\nhello"}
