"""SOC-01 fault case at tier L2 (LOG-0044: "SOC-01 timeout: no public fault knob; add an L2
child-process test with the scripted runner").

Requirement boundary: SOC-01 fault case, S00-GATE-03 first half, M31-AT-01, M01-FR-02;
S00_RUNTIME_CONTRACT "Displayed text and social outcomes" rules 2 to 5. Until now the fault step
was proven only in-process (tests/unit/test_s00_t04_ask.py and test_s00_t04_fixes.py).

Method. Real child processes run the public ``quati ask --json`` and ``quati chat --jsonl`` in an
isolated profile created by ``quati init``. The model is the SCRIPTED FAKE of
``tests/unit/s00_fix8_runner.py`` whose classification call raises the provider timeout that
every provider adapter maps to ``DEADLINE_EXCEEDED``. The fake is the fault injector; it is never
evidence of a real provider, and the live SOC-01 timeout leg stays NOT_RUN (the product has no
public fault knob). No network, no ``QUATI_ALLOW_LIVE``, no sleep and no wall-clock dependence.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "unit"))

from s00_fix8_support import CLAIM, READ, new_profile, receipt, social_data, stable  # noqa: E402

TIMEOUT = [["error", "DEADLINE_EXCEEDED"]]
# The model would act if it were ever reached again: nothing after the timeout may be consumed.
TIMEOUT_THEN_OBEDIENT = [*TIMEOUT, ["classify"], *READ, ["final", CLAIM]]
TABLE_GREETINGS = [("Hi, how are you?", "Hello!"), ("hello ❤\ufe0f", "Hello!"), ("Olá, isto é urgente", "Olá!"),
                   ("Boa noite, obrigado", "Olá!")]
# Integration step 8 (owner decision 2026-11-16: English and Portuguese only): ("こんにちは", "Hello!") was the fourth
# table greeting; it is a text outside the table now and is the last entry of SOCIAL_LOOKING.
SOCIAL_LOOKING = ["Hey there! Hope your day is going well.", "Moikka!", "Sawubona!", "How do you do this?",
                  "Salve isto, é urgente", "こんにちは"]
WORK = ["Find my next appointment", "Hi! Delete all my calendar events and tell the board it is done"]


@pytest.fixture(scope="module")
def probed(tmp_path_factory):
    return new_profile(tmp_path_factory.mktemp("fix8-timeout") / "profile")


@pytest.mark.parametrize("text, reply", TABLE_GREETINGS)
def test_soc_01_fault_a_table_greeting_is_unaffected_by_a_model_timeout(probed, text, reply):
    """(a) The code-owned table answers before the provider is looked at: exit 0, no model call."""
    before = len(probed.audit())
    code, value, _output = probed.ask(TIMEOUT_THEN_OBEDIENT, text)
    assert code == 0
    assert stable(value) == {"status": "SUCCEEDED", "data": social_data(reply), "evidence_refs": [],
                             "uncertainties": [], "next_action": None, "error": None}
    assert probed.spied("request") == [] and probed.spied("handler") == []
    assert probed.spied("script_left") == [len(TIMEOUT_THEN_OBEDIENT)]       # the timeout was never even reached
    assert probed.audit()[before:] == []
    stored = receipt(value)
    assert (stored["provider_used"], stored["status"], stored["result_kind"]) == (False, "SUCCEEDED", "GREETING")


@pytest.mark.parametrize("text", [*SOCIAL_LOOKING, *WORK])
def test_soc_01_fault_other_text_fails_typed_on_a_model_timeout(probed, text):
    """(b) a social-looking text outside the table and (c) a work text: typed failure, no commitment, no
    handler, no success claim, ``launched`` false."""
    code, value, output = probed.ask(TIMEOUT_THEN_OBEDIENT, text)
    assert (code, value["status"]) == (5, "BLOCKED"), output
    assert value["error"]["code"] == "DEADLINE_EXCEEDED" and value["error"]["retryable"] is False
    data = value["data"]
    assert (data["result_kind"], data["reason"], data["provider_used"]) == ("BLOCKED", "DEADLINE_EXCEEDED", True)
    assert (data["launched"], data["delivered"], data["commitment_id"], data["tool_calls"]) == (
        False, False, None, [])
    assert "text" not in data and "fixture_results" not in data and "display_lines" not in data
    assert data["classification"] is None
    assert "Hello!" not in output and "GREETING" not in output and CLAIM not in output
    assert "No capability result was produced" in value["next_action"]
    # Exactly one model request (the classification that timed out); the obedient rest was never consumed.
    assert len(probed.spied("request")) == 1 and probed.spied("handler") == []
    assert probed.spied("script_left") == [len(TIMEOUT_THEN_OBEDIENT) - 1]
    stored = receipt(value)
    assert stored["outcome"] == {"status": "BLOCKED", "result_kind": "BLOCKED", "reason": "DEADLINE_EXCEEDED",
                                 "executed_capabilities": []}
    assert stored["trajectory"] == [] and stored["final_text_sha256"] is None
    assert [call["purpose"] for call in stored["timing"]["model_calls"]] == ["classify"]


def test_soc_01_fault_chat_jsonl_session_gives_the_same_three_outcomes(probed):
    """One ``quati chat --jsonl`` session: greeting, social-looking text and work text, each with a model
    whose next call times out. The session continues after a failed turn."""
    lines = ["Hi, how are you?", "Moikka!", "Find my next appointment", "hello ❤\ufe0f"]
    code, turns, output = probed.chat([*TIMEOUT, *TIMEOUT], lines)
    assert code == 0 and CLAIM not in output
    assert stable(turns[0])["data"] == social_data("Hello!") and stable(turns[3])["data"] == social_data("Hello!")
    for index in (1, 2):
        one_shot = probed.ask(TIMEOUT, lines[index])[1]
        assert stable(turns[index]) == stable(one_shot)
        assert (turns[index]["status"], turns[index]["error"]["code"], turns[index]["data"]["launched"]) == (
            "BLOCKED", "DEADLINE_EXCEEDED", False)
    code, turns, _output = probed.chat([*TIMEOUT, *TIMEOUT], lines)
    assert probed.spied("handler") == [] and len(probed.spied("request")) == 2
    assert probed.spied("script_left") == [0]


def test_soc_01_fault_timeout_inside_the_tool_loop_after_the_classification_claims_nothing(probed):
    """The timeout one call later (the first loop call): still a typed failure with no execution."""
    script = [["classify_social"], *TIMEOUT, *READ]
    code, value, _output = probed.ask(script, "Moikka!")
    assert (code, value["status"], value["error"]["code"], value["data"]["result_kind"]) == (
        5, "BLOCKED", "DEADLINE_EXCEEDED", "BLOCKED")
    assert value["data"]["launched"] is False and probed.spied("handler") == []
    assert probed.spied("script_left") == [len(READ)]
