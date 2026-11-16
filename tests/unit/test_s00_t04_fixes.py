"""S00-T04 fix round after the independent audit and the claude_cli haiku pilot (T05 pilot1/pilot2).

Each test names the audit finding it discriminates (P1-1, P2-1..P2-6, P3, L1, L2, L3).
Proof tier L1 with a SCRIPTED FAKE model (tests/unit/s00_t04_support.py) or a scripted
child-process runner; no network, no real provider and no ``QUATI_ALLOW_LIVE``.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from s00_t04_support import (  # noqa: E402
    CALENDAR_QUERY, FAKE_TRANSPORT, SOCIAL, WORK, Harness, Script, ScriptedFakeProvider, classified, describe, final,
    invoke, receipt_bytes, receipt_of, search, status_of)
from quati.application import ask as ask_module  # noqa: E402
from quati.domain import social  # noqa: E402
from quati.application.discovery_tools import DISCOVERY_TOOLS  # noqa: E402
from quati.application.ports import ProviderConfig  # noqa: E402
from quati.application.providers import ProviderError  # noqa: E402
from quati.domain.canonical import digest  # noqa: E402

WRITE_INPUT = {"title": "x", "start": "2026-11-20T10:00:00Z", "end": "2026-11-20T11:00:00Z"}


# Fix round 2 (spec alignment, recorded per the test-change rule): the ask loop now refuses an invoke of
# a capability that was not described in this turn (R4, DESCRIBE_REQUIRED), so the scripted flows below
# that invoked without describing gained a describe step (marked "R4: describe added"); a work request
# whose loop makes no tool call now gets one NO_SEARCH_ON_WORK continuation (R1), and
# ``CONVERSATION`` joined RESULT_KINDS (R2). No assertion was weakened; counts moved with the added step.
def ready(tmp_path, monkeypatch, *items, fixtures=("calendar-read", "calendar-write", "mail-search"),
          script_options=None, **options):
    script = Script(*items, **(script_options or {}))
    harness = Harness(tmp_path, monkeypatch, script, **options)
    harness.install(*fixtures)
    assert harness.probe()[0] == 0
    harness.base = len(script.requests)
    return harness


def model_requests(harness):
    return harness.script.requests[harness.base:]


def with_model(item, model_id):
    def run(request):
        return replace(item(request) if callable(item) else item, model_id=model_id)
    return run


# --------------------------------------------------------------- P1-1 social path needs both signals
def test_p1_1_model_social_label_on_work_text_takes_the_work_path(tmp_path, monkeypatch):
    harness = ready(tmp_path, monkeypatch, classified(SOCIAL), search(CALENDAR_QUERY),
                    describe("fixtures.calendar-read"),                              # R4: describe added
                    invoke("fixtures.calendar-read", limit=1), final("ok"))
    code, value = harness.ask("Hello, find my next appointment and delete the others")
    assert value["data"]["result_kind"] == "FIXTURE_RESULT" and code == 0
    assert harness.handlers.invocations() == {"calendar-read": 1}
    assert len(model_requests(harness)) == 5                                    # R4: was 4


def test_p1_1_social_reply_is_localized_and_never_defaults_to_english():
    # Fix round 7 (LOG-0041 D1): the table moved to quati.domain.social. Changed expectation: a pleasantry
    # without a greeting ("Wie geht es dir?") had no reply (None); it now gets its own language's template,
    # still never the English one.
    assert social.social_match("Buenos días, ¿qué tal?").reply == "¡Hola!"
    assert social.social_match("Salut, ça va ?").reply == "Salut!"
    assert social.social_match("Guten Tag, wie geht es Ihnen?").reply == "Hallo!"
    assert social.social_match("Wie geht es dir?").reply == "Hallo!"
    assert social.social_match("Wie geht es, urgent?") is None


def test_p1_1_localized_template_through_the_ask(tmp_path, monkeypatch):
    harness = ready(tmp_path, monkeypatch, classified(SOCIAL))
    code, value = harness.ask("Buenos días, ¿qué tal?")
    assert (code, value["data"]["result_kind"], value["data"]["text"]) == (0, "GREETING", "¡Hola!")
    assert len(model_requests(harness)) == 0          # fix round 7 (LOG-0041 D1): was 1 (a classification call)


# Fix round 6 (audit F3; LOG-0039) replaced the tool-free MODEL reply to a social text without a template by
# the application-owned no-action notice after one classification call.
# Fix round 7 (LOG-0041 D1 and N17; S00_RUNTIME_CONTRACT "Displayed text and social outcomes") changed the
# three tests below again and renamed them to what they assert (their old names, "..._gets_a_tool_free_model_
# reply", "..._tool_free_social_reply_failures_are_typed" and "..._provider_failure_fallback_needs_a_template",
# described the round 5 behavior). Old: text == the no-action notice, uncertainty NO_GREETING_TEMPLATE, one
# classification request, and a failing classification was exit 5. New: the template of the text's language,
# no uncertainty, no model request at all, so no provider state can change or fail a social-only text; a text
# that is not social-only keeps the typed provider failure.
@pytest.mark.parametrize("text, reply", [("Wie geht es dir?", "Hallo!"), ("How are you doing today?", "Hello!")])
def test_p1_1_social_text_without_a_greeting_gets_the_application_template_and_no_model_call(
        tmp_path, monkeypatch, text, reply):
    harness = ready(tmp_path, monkeypatch, classified(SOCIAL), final("  Mir geht es gut, danke!  "))
    code, value = harness.ask(text, synthetic=True)
    assert (code, value["status"], value["data"]["result_kind"]) == (0, "SUCCEEDED", "GREETING")
    assert value["data"]["text"] == reply and value["data"]["text_source"] == "application_template"
    assert "Mir geht es gut" not in json.dumps(value)
    assert value["uncertainties"] == [] and value["data"]["tool_calls"] == []
    assert len(model_requests(harness)) == 0 and len(harness.script.items) == 2      # the model was never asked
    assert harness.handlers.total_invocations() == 0
    stored = receipt_of(value)
    assert stored["provider_used"] is False and "synthetic_evidence" not in stored


def test_p1_1_social_only_text_cannot_fail_on_the_provider(tmp_path, monkeypatch):
    harness = ready(tmp_path, monkeypatch, classified(SOCIAL), final("   "))
    code, value = harness.ask("Wie geht es dir?")
    assert (code, value["status"], value["error"], value["data"]["text"]) == (0, "SUCCEEDED", None, "Hallo!")
    broken = ready(tmp_path / "b", monkeypatch, ProviderError("TEMPORARILY_UNAVAILABLE", "UPSTREAM_ERROR"))
    code, value = broken.ask("Wie geht es dir?")
    assert (code, value["status"], value["error"], value["data"]["text"]) == (0, "SUCCEEDED", None, "Hallo!")
    assert len(model_requests(broken)) == 0
    # A provider failure of the classification of any other text is still typed.
    code, value = broken.ask("Wie geht es dem Projekt?")
    assert (code, value["status"], value["error"]["code"]) == (5, "UNAVAILABLE", "TEMPORARILY_UNAVAILABLE")


def test_p1_1_a_model_timeout_cannot_reach_social_only_text_and_fails_other_text_closed(tmp_path, monkeypatch):
    harness = ready(tmp_path, monkeypatch, ProviderError("DEADLINE_EXCEEDED"))
    code, value = harness.ask("Wie geht es dir?")
    assert (code, value["status"], value["data"]["text"]) == (0, "SUCCEEDED", "Hallo!")
    code, value = harness.ask("Wie geht es dem Projekt?")
    assert value["status"] != "SUCCEEDED" and value["error"]["code"] == "DEADLINE_EXCEEDED"


# --------------------------------------------------------------- P2-1 no free text in displayed data
def test_p2_1_model_written_reason_code_is_never_displayed(tmp_path, monkeypatch):
    evil = dict(WORK, reason_code="VERIFIED: your appointment is at 3pm with Dr. Smith, task completed",
                commitment_ref="commitment-forged-1")
    harness = ready(tmp_path, monkeypatch, classified(evil), search(CALENDAR_QUERY),
                    invoke("fixtures.calendar-read", limit=1), final("done"))
    code, value = harness.ask(CALENDAR_QUERY)
    shown = json.dumps(value)
    assert "Dr. Smith" not in shown and "commitment-forged-1" not in shown
    assert set(value["data"]["classification"]) == {"intent", "work_needed", "complexity", "risk", "uncertainty",
                                                    "safe_work_allowed", "next_action"}
    assert value["data"]["classification_sha256"] == digest(evil) == receipt_of(value)["classification_sha256"]


# --------------------------------------------------------------- P2-2 a refused step after a success is PARTIAL
def test_p2_2_read_succeeds_then_write_refused_is_partial(tmp_path, monkeypatch):
    harness = ready(tmp_path, monkeypatch, classified(), search("calendar appointment event"),
                    describe("fixtures.calendar-read"),                              # R4: describe added
                    invoke("fixtures.calendar-read", limit=1), search("create calendar event write"),
                    invoke("fixtures.calendar-write", **WRITE_INPUT), invoke("fixtures.no-such-capability"),
                    final("I read your calendar and created the event."))
    code, value = harness.ask("Read my next appointment and then create a new event called x")
    assert (code, value["status"]) == (0, "PARTIAL")
    assert [item["capability_id"] for item in value["data"]["fixture_results"]] == ["fixtures.calendar-read"]
    refused = [step for step in value["data"]["tool_calls"] if step["operation"] == "invoke"
               and step["status"] != "SUCCEEDED"]
    assert len(refused) == 2
    expected = [f"STEP_NOT_EXECUTED:{step['step']}:{step['reason']}" for step in refused]
    assert [note for note in value["uncertainties"] if note.startswith("STEP_NOT_EXECUTED:")] == expected
    assert harness.handlers.invocations() == {"calendar-read": 1}
    assert receipt_of(value)["outcome"]["executed_capabilities"] == ["fixtures.calendar-read@1.0.0"]


def test_p2_2_refusal_before_the_success_does_not_downgrade(tmp_path, monkeypatch):
    harness = ready(tmp_path, monkeypatch, classified(), invoke("fixtures.calendar-read", limit=1),
                    search(CALENDAR_QUERY), describe("fixtures.calendar-read"),       # R4: describe added
                    invoke("fixtures.calendar-read", limit=1), final("ok"))
    code, value = harness.ask(CALENDAR_QUERY)
    assert (code, value["status"]) == (0, "SUCCEEDED")


# --------------------------------------------------------------- P2-3 model identity binds the gate
def test_p2_3_response_from_another_model_fails_closed(tmp_path, monkeypatch):
    items = (classified(), search(CALENDAR_QUERY), invoke("fixtures.calendar-read", limit=1), final("ok"))
    harness = ready(tmp_path, monkeypatch, *[with_model(item, "totally-different-model-9") for item in items])
    code, value = harness.ask(CALENDAR_QUERY)
    assert (code, value["status"], value["error"]["code"], value["data"]["reason"]) == (
        4, "UNAVAILABLE", "UNSUPPORTED", "MODEL_ID_MISMATCH")
    assert harness.handlers.total_invocations() == 0 and len(model_requests(harness)) == 1
    empty = ready(tmp_path / "e", monkeypatch, *[with_model(item, "") for item in items])
    code, value = empty.ask(CALENDAR_QUERY)
    assert (value["status"], value["data"]["reason"]) == ("UNAVAILABLE", "MODEL_ID_UNOBSERVED")


def test_p2_3_mismatch_inside_the_loop_stops_before_any_invoke(tmp_path, monkeypatch):
    harness = ready(tmp_path, monkeypatch, classified(), search(CALENDAR_QUERY),
                    with_model(invoke("fixtures.calendar-read", limit=1), "swapped-model"), final("ok"))
    code, value = harness.ask(CALENDAR_QUERY)
    assert value["data"]["reason"] == "MODEL_ID_MISMATCH" and harness.handlers.total_invocations() == 0


def test_p2_3_probe_without_an_observed_model_id_does_not_open_the_gate(tmp_path, monkeypatch):
    script = Script(classified(), search(CALENDAR_QUERY), final(), probe_model_id="")
    harness = Harness(tmp_path, monkeypatch, script)
    harness.install("calendar-read")
    code, probe = harness.probe()
    report = probe["data"]["feature_report"]
    assert report["observed_model_id"] == "" and report["features"]["tools"] == "SUPPORTED"
    before = len(script.requests)
    code, value = harness.ask(CALENDAR_QUERY)
    assert (code, value["status"], value["error"]["code"]) == (4, "UNAVAILABLE", "UNSUPPORTED")
    assert value["data"]["feature_support"] == "NOT_VERIFIED"
    assert "MODEL_ID_UNOBSERVED" in value["uncertainties"] and len(script.requests) == before
    assert receipt_of(value)["feature_gate"]["reason"] == "MODEL_ID_UNOBSERVED"


def test_p2_3_probe_records_the_observed_model_id(tmp_path, monkeypatch):
    harness = ready(tmp_path, monkeypatch, classified(), final())
    gate = receipt_of(harness.ask(CALENDAR_QUERY)[1])["feature_gate"]
    assert gate["observed_model_id"] == "fake-model-1" and gate["reason"] is None


def test_p2_3_cli_executable_identity_is_part_of_the_config_hash(tmp_path):
    from quati.adapters.providers.cli import ClaudeCliProvider
    executable = tmp_path / "claude"
    executable.write_bytes(b"#!/bin/sh\necho 1.0\n")
    found = {"path": str(executable)}
    provider = ClaudeCliProvider(ProviderConfig(transport="claude_cli", allow_live=True),
                                 which=lambda name: found["path"])
    first = provider.config_hash()
    assert provider.config_hash() == first                                     # stable while nothing changes
    executable.write_bytes(b"#!/bin/sh\necho 2.0 upgraded\n")
    upgraded = provider.config_hash()
    assert upgraded != first
    stat = executable.stat()
    os.utime(executable, ns=(stat.st_atime_ns, stat.st_mtime_ns + 10**9))
    assert provider.config_hash() not in (first, upgraded)
    found["path"] = None
    missing = provider.config_hash()
    assert missing not in (first, upgraded)
    found["path"] = str(tmp_path / "removed-claude")                            # on PATH earlier, now unreadable
    assert provider.executable_identity()["size"] is None and provider.config_hash() not in (first, missing)
    identity = ClaudeCliProvider(ProviderConfig(transport="claude_cli"), which=lambda name: str(executable))
    assert identity.executable_identity()["realpath"] == str(executable.resolve())


def test_p2_3_codex_reports_the_model_id_from_its_json_events():
    from quati.adapters.providers.cli import CodexCliProvider, codex_model_id
    from quati.application.providers import Message, ModelRequest
    from test_provider_adapters import Runner, make_cli
    events = "\n".join([json.dumps({"type": "thread.started", "thread_id": "t-1"}), "not json",
                        json.dumps({"id": "0", "msg": {"type": "session_configured", "model": "gpt-observed-1"}}),
                        json.dumps({"type": "turn.completed", "usage": {"input_tokens": 3}})])
    # Fix round 3 (LOG-0029 root decision, recorded change): with a configured model the codex response
    # id is that requested name (codex-cli 0.169.0 never names one); the observed-event parsing is kept
    # for the no-configured-model case. Previously: "gpt-observed-1", then "" for the second call.
    runner = Runner((0, events), (0, ""), write=["hi", "hi"])
    provider = make_cli(CodexCliProvider, runner, model="gpt-configured")
    request = ModelRequest((Message("user", "hello"),))
    assert provider.complete(request).model_id == "gpt-configured"
    assert "--json" in runner.calls[0]["argv"]
    assert provider.complete(request).model_id == "gpt-configured"            # requested, not observed
    unset = make_cli(CodexCliProvider, Runner((0, events), (0, ""), write=["hi", "hi"]))
    assert unset.complete(request).model_id == "gpt-observed-1"                # an event naming a model
    assert unset.complete(request).model_id == ""                              # nothing observed, gate closed
    assert codex_model_id(json.dumps({"type": "x", "model": "top-level-1"})) == "top-level-1"
    assert codex_model_id(json.dumps({"payload": {"model": ""}}) + "\n[1]\n" + json.dumps({"msg": "text"})) == ""


# --------------------------------------------------------------- P2-4 per-transport ask deadline
def test_p2_4_cli_transports_get_the_cli_budget_and_config_can_only_lower_it(tmp_path, monkeypatch):
    from quati.adapters.providers.cli import ClaudeCliProvider
    from quati.adapters.providers.openai_compatible import OpenAICompatibleProvider
    assert ask_module.ask_deadline_seconds(ClaudeCliProvider(ProviderConfig(transport="claude_cli"))) == 180
    assert ask_module.ask_deadline_seconds(OpenAICompatibleProvider(ProviderConfig(transport="openai_compatible"))) == 30
    lowered = ProviderConfig(transport="claude_cli", ask_deadline_seconds=45)
    assert ask_module.ask_deadline_seconds(ClaudeCliProvider(lowered)) == 45
    raised = ProviderConfig(transport="claude_cli", ask_deadline_seconds=900)
    assert ask_module.ask_deadline_seconds(ClaudeCliProvider(raised)) == 180


def test_p2_4_cli_budget_lets_a_slow_cli_flow_finish(tmp_path, monkeypatch):
    monkeypatch.setattr(ScriptedFakeProvider, "executable", "fake-cli")
    monkeypatch.setattr(ScriptedFakeProvider, "_which", lambda self, name: "/usr/bin/true")
    harness = ready(tmp_path, monkeypatch, classified(), search(CALENDAR_QUERY),
                    describe("fixtures.calendar-read"),                              # R4: describe added
                    invoke("fixtures.calendar-read", limit=1), final("ok"))
    # R4: five calls now, so 30 s each (was 40 s x 4 = 160 s); 150 s still far exceeds the 30 s HTTP budget.
    harness.script.before_call = lambda request: harness.clock.advance(30)
    code, value = harness.ask(CALENDAR_QUERY)
    assert (code, value["status"]) == (0, "SUCCEEDED")                         # 150 s on the injected clock
    assert receipt_of(value)["effective_limits"]["deadline_s"] == 180
    for request in model_requests(harness):
        assert request.timeout_s <= 60                                          # config timeout_seconds default


def test_p2_4_the_ask_deadline_is_not_reported_as_a_provider_failure(tmp_path, monkeypatch):
    harness = ready(tmp_path, monkeypatch, classified(), search(CALENDAR_QUERY), final())
    harness.script.before_call = lambda request: harness.clock.advance(ask_module.ASK_DEADLINE_S + 1)
    code, value = harness.ask(CALENDAR_QUERY)
    assert (code, value["error"]["code"], value["data"]["reason"]) == (5, "DEADLINE_EXCEEDED", "ASK_DEADLINE")
    assert "ASK_DEADLINE" in value["uncertainties"] and "provider" not in value["next_action"].lower()
    assert len(model_requests(harness)) == 1


def test_p2_4_provider_timeout_past_the_ask_deadline_is_the_ask_deadline(tmp_path, monkeypatch):
    harness = ready(tmp_path, monkeypatch, classified(), ProviderError("DEADLINE_EXCEEDED"))
    calls = []

    def late(request):
        calls.append(request)
        if len(calls) == 2:
            harness.clock.advance(ask_module.ASK_DEADLINE_S)
    harness.script.before_call = late
    code, value = harness.ask(CALENDAR_QUERY)
    assert value["data"]["reason"] == "ASK_DEADLINE"
    plain = ready(tmp_path / "p", monkeypatch, classified(), ProviderError("DEADLINE_EXCEEDED"))
    code, value = plain.ask(CALENDAR_QUERY)
    assert (value["error"]["code"], value["data"]["reason"]) == ("DEADLINE_EXCEEDED", "DEADLINE_EXCEEDED")


def test_p2_4_configured_deadline_lowers_the_ask_budget(tmp_path, monkeypatch):
    config = ProviderConfig(transport=FAKE_TRANSPORT, allow_live=True, ask_deadline_seconds=10)
    harness = ready(tmp_path, monkeypatch, classified(), search(CALENDAR_QUERY), final(), config=config)
    harness.script.before_call = lambda request: harness.clock.advance(11)
    code, value = harness.ask(CALENDAR_QUERY)
    assert value["data"]["reason"] == "ASK_DEADLINE" and len(model_requests(harness)) == 1


# --------------------------------------------------------------- P3 configured caps are respected
def test_p3_configured_output_tokens_and_timeout_lower_the_ask_caps(tmp_path, monkeypatch):
    config = ProviderConfig(transport=FAKE_TRANSPORT, allow_live=True, timeout_seconds=7, max_output_tokens=512)
    harness = ready(tmp_path, monkeypatch, classified(), search(CALENDAR_QUERY),
                    describe("fixtures.calendar-read"),                              # R4: describe added
                    invoke("fixtures.calendar-read", limit=1), final(), config=config)
    code, value = harness.ask(CALENDAR_QUERY)
    assert code == 0 and model_requests(harness)
    for request in model_requests(harness):
        assert request.max_output_tokens == 512 and 0 < request.timeout_s <= 7
    generous = ProviderConfig(transport=FAKE_TRANSPORT, allow_live=True, max_output_tokens=100000)
    harness = ready(tmp_path / "g", monkeypatch, classified(), final(), config=generous)
    harness.ask(CALENDAR_QUERY)
    assert all(request.max_output_tokens == ask_module.ASK_MAX_OUTPUT_TOKENS for request in model_requests(harness))


def test_p3_model_visible_hashes_are_split_and_named_for_what_they_cover(tmp_path, monkeypatch):
    harness = ready(tmp_path, monkeypatch, classified(), search(CALENDAR_QUERY),
                    invoke("fixtures.calendar-read", limit=1), final())
    code, value = harness.ask(CALENDAR_QUERY, synthetic=True)
    evidence = receipt_of(value)["synthetic_evidence"]
    visible = evidence["model_visible"]
    loop_system = model_requests(harness)[1].system
    assert visible["system_prompt_sha256"] == hashlib.sha256(loop_system.encode()).hexdigest()
    assert visible["system_and_tools_sha256"] == evidence["digests"]["effective_prompt_hash"]
    assert visible["tools_sha256"] == evidence["digests"]["tool_schema_digest"]


# --------------------------------------------------------------- P2-5 capability_ref only for registry keys
def test_p2_5_unresolved_model_supplied_id_is_recorded_as_a_digest(tmp_path, monkeypatch):
    marker = "fixtures.private-marker-991"
    harness = ready(tmp_path, monkeypatch, classified(), search(CALENDAR_QUERY), describe(marker), invoke(marker),
                    invoke("fixtures.calendar-read", limit=1), final())
    code, value = harness.ask(CALENDAR_QUERY)
    steps = value["data"]["tool_calls"]
    assert steps[1]["capability_ref"] == steps[2]["capability_ref"] == "sha256:" + digest(marker)
    assert steps[3]["capability_ref"] == "fixtures.calendar-read@1.0.0"
    assert "private-marker-991" not in json.dumps(value) and b"private-marker-991" not in receipt_bytes(value)


# --------------------------------------------------------------- P2-6 per-call timing on the injected clock
def test_p2_6_model_calls_carry_injected_clock_timing(tmp_path, monkeypatch):
    harness = ready(tmp_path, monkeypatch, classified(), search(CALENDAR_QUERY),
                    describe("fixtures.calendar-read"),                              # R4: describe added
                    invoke("fixtures.calendar-read", limit=1), final())
    harness.script.before_call = lambda request: harness.clock.advance(2)
    start = harness.clock()
    code, value = harness.ask(CALENDAR_QUERY, synthetic=True)
    receipt = receipt_of(value)
    calls = receipt["synthetic_evidence"]["model_calls"]
    assert [call["elapsed_s"] for call in calls] == [2.0] * 5                   # R4: was 4 calls
    assert calls[0]["started_at"] == start.isoformat()
    assert all(call["ended_at"] == later["started_at"] for call, later in zip(calls, calls[1:]))
    timing = receipt["timing"]
    assert timing["model_calls"] == [{"index": call["index"], "purpose": call["purpose"], "elapsed_s": 2.0}
                                     for call in calls]
    assert (timing["model_elapsed_s"], timing["ask_elapsed_s"]) == (10.0, 10.0)   # R4: was 8.0 (4 calls)
    plain = ready(tmp_path / "d", monkeypatch, classified(), final())
    assert "timing" in receipt_of(plain.ask(CALENDAR_QUERY)[1])


# --------------------------------------------------------------- L1 English keyword search
def test_l1_search_guidance_says_the_catalog_is_english(tmp_path, monkeypatch):
    search_tool = next(tool for tool in DISCOVERY_TOOLS if tool.name == "quati_search")
    assert "written in English" in search_tool.description and "short English keywords" in search_tool.description
    harness = ready(tmp_path, monkeypatch, classified(), search("próxima consulta"), search("next appointment"),
                    describe("fixtures.calendar-read"),                              # R4: describe added
                    invoke("fixtures.calendar-read", limit=1), final())
    code, value = harness.ask("Qual é a minha próxima consulta?")
    assert code == 0 and value["status"] == "SUCCEEDED"                        # a second search is allowed
    system = model_requests(harness)[1].system
    assert "catalog entries are written in English" in system and "short English keywords" in system
    assert "whatever language" in system and "search again" in system


# --------------------------------------------------------------- L2 progress text instead of invoke
def test_l2_system_prompt_forbids_progress_messages(tmp_path, monkeypatch):
    harness = ready(tmp_path, monkeypatch, classified(), final())
    harness.ask(CALENDAR_QUERY)
    system = model_requests(harness)[1].system
    assert "only sees your final message" in system and "Do not send progress messages" in system
    assert "invoke the chosen capability before replying" in system


def test_l2_one_bounded_continuation_after_progress_text(tmp_path, monkeypatch):
    harness = ready(tmp_path, monkeypatch, classified(), search(CALENDAR_QUERY),
                    final("Let me check your calendar now..."), describe("fixtures.calendar-read"),  # R4: added
                    invoke("fixtures.calendar-read", limit=1), final("ok"))
    code, value = harness.ask(CALENDAR_QUERY, synthetic=True)
    assert (code, value["data"]["result_kind"]) == (0, "FIXTURE_RESULT")
    continued = model_requests(harness)[3]
    assert continued.messages[-1].content == ask_module.CONTINUATION_TEXT
    assert continued.messages[-2].role == "assistant"
    evidence = receipt_of(value)["synthetic_evidence"]
    assert [call["purpose"] for call in evidence["model_calls"]] == [
        "classify", "loop", "loop", "loop_continuation", "loop", "loop"]       # R4: one more loop call
    assert evidence["continuations"] == [{"after_step": 1, "reason": "NO_INVOKE_WITH_SHORTLIST"}]
    assert receipt_of(value)["continuations"] == evidence["continuations"]


def test_l2_continuation_happens_at_most_once_and_never_auto_invokes(tmp_path, monkeypatch):
    harness = ready(tmp_path, monkeypatch, classified(), search(CALENDAR_QUERY), final("Working on it"),
                    final("Still working"), final("never requested"))
    code, value = harness.ask(CALENDAR_QUERY)
    assert (value["status"], value["error"]["code"], value["data"]["reason"]) == (
        "BLOCKED", "EVIDENCE_INSUFFICIENT", "NO_VERIFIED_EXECUTION")
    assert len(model_requests(harness)) == 4 and harness.handlers.total_invocations() == 0
    assert len(harness.script.items) == 1


@pytest.mark.parametrize("items", [
    (search("zzqx unrelated vocabulary"), final("Done")),                         # empty shortlist
    (search(CALENDAR_QUERY), invoke("NONE_FITS"), final("Nothing fits")),       # NONE_FITS attempted
    (search(CALENDAR_QUERY), invoke("fixtures.calendar-write", title="x"), final("Refused")),  # invoke attempted
    # R1 superseded the former case ``(final("Done!"),)`` (no search at all): a work request whose loop
    # makes no tool call now gets one NO_SEARCH_ON_WORK continuation; see test_s00_t04_fixes2.py R1 tests.
])
def test_l2_no_continuation_without_a_shortlist_or_after_a_choice(tmp_path, monkeypatch, items):
    harness = ready(tmp_path, monkeypatch, classified(), *items)
    harness.ask(CALENDAR_QUERY)
    assert len(model_requests(harness)) == 1 + len(items)
    assert all(ask_module.CONTINUATION_TEXT not in request.messages[-1].content
               for request in model_requests(harness))


def test_l2_continuation_counts_against_the_request_budget(tmp_path, monkeypatch):
    invalid = classified({"intent": "x"})
    harness = ready(tmp_path, monkeypatch, invalid, invalid, classified(), search(CALENDAR_QUERY),
                    *[describe("fixtures.calendar-read")] * 3, final("progress"), final("x"))
    code, value = harness.ask(CALENDAR_QUERY)
    assert len(model_requests(harness)) == ask_module.ASK_MAX_PROVIDER_REQUESTS
    assert (value["error"]["code"], value["data"]["reason"]) == ("BUDGET_EXCEEDED", "MODEL_REQUEST_BUDGET")


# --------------------------------------------------------------- L3 status consistency
def test_l3_none_fits_and_empty_shortlist_are_no_capability(tmp_path, monkeypatch):
    for index, items in enumerate([(search("translate this poem into Latin"), invoke("NONE_FITS"), final("x")),
                                   (search("zzqx unrelated vocabulary"), final("Done"))]):
        harness = ready(tmp_path / str(index), monkeypatch, classified(), *items)
        code, value = harness.ask("Translate this poem into Latin")
        data = value["data"]
        # Fix round 8 (LOG-0044 decision D7): was (0, "SUCCEEDED", "report_no_capability") and
        # `"FIXTURE_RESULT" not in data["text"]`. No capability is a typed non-success (exit 4) that keeps its
        # result kind; it has no `text` (the sentence is the error message), so no fixture result can be in it.
        assert (code, value["status"], value["error"]["code"]) == (4, "UNAVAILABLE", "UNSUPPORTED")
        assert "No installed capability" in value["next_action"] and "report_no_capability" not in json.dumps(value)
        assert (data["result_kind"], data["result_status"], data["outcome"]) == (
            "NO_CAPABILITY", "NO_CAPABILITY", "NO_CAPABILITY")
        assert "fixture_results" not in data and "text" not in data and "FIXTURE_RESULT" not in json.dumps(value)
        assert receipt_of(value)["outcome"]["result_kind"] == "NO_CAPABILITY"


def test_l3_model_stopped_without_invoking_is_distinguishable(tmp_path, monkeypatch):
    # R1: the tool-free work loop gets one NO_SEARCH_ON_WORK continuation, so a second final was added.
    harness = ready(tmp_path, monkeypatch, classified(), final("Done!"), final("Done!"))
    code, value = harness.ask(CALENDAR_QUERY)
    assert (value["status"], value["error"]["code"], value["data"]["result_kind"]) == (
        "BLOCKED", "EVIDENCE_INSUFFICIENT", "BLOCKED")
    assert value["next_action"] != "report_no_capability"


def test_l3_result_kinds_are_documented():
    # Fix round 7 (LOG-0041 D2): CONVERSATION (added by R2) no longer exists; S00 displays no model answer.
    assert ask_module.RESULT_KINDS == ("GREETING", "FIXTURE_RESULT", "NO_CAPABILITY", "BLOCKED")
    for kind in ask_module.RESULT_KINDS:
        assert f"``{kind}``" in ask_module.__doc__, kind
