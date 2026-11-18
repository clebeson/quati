"""S00-T04 local assertions A01-A04 (M17-FR-02, M17-RT-01, M17-RT-02, M17-AT-01/02 contribution, M31-FR-02/03,
M26-FR-02 contribution, CAP-05 contribution, K8).

Proof tier L1: the model is a SCRIPTED FAKE ``Provider`` subclass (tests/unit/s00_t04_support.py).
No network, no real provider, no ``QUATI_ALLOW_LIVE``. A real nonce round-trip with a real
provider is only proven by tests/external (see test_a02 docstring).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from s00_t04_support import (  # noqa: E402
    CALENDAR_QUERY, WORK, Harness, Script, classified, describe, final, invoke, receipt_bytes, receipt_of, search,
    status_of, tool)
from quati.application import ask as ask_module  # noqa: E402
from quati.application.ports import ProviderConfig  # noqa: E402
from quati.application.providers import ModelResponse, ProviderError  # noqa: E402

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _refused_incompatible(code, value, harness, before_requests):
    assert code == 4
    assert (value["status"], value["error"]["code"]) == ("UNAVAILABLE", "UNSUPPORTED")
    assert value["data"]["reason"] == "MODEL_INCOMPATIBLE"
    assert "MODEL_INCOMPATIBLE" in value["uncertainties"]
    assert value["data"]["provider_used"] is False and value["data"]["tool_calls"] == []
    assert len(harness.script.requests) == before_requests          # no classification, no loop call
    assert harness.handlers.total_invocations() == 0                # zero binding calls


# --------------------------------------------------------------------------- A01
def test_a01(tmp_path, monkeypatch):
    """S00-T04-A01: unknown tool support remains unverified; UNKNOWN is never SUPPORTED (CAP-05, M17-RT-01)."""
    script = Script(probe_tools="fail")
    harness = Harness(tmp_path, monkeypatch, script)
    harness.install("calendar-read")
    # 1. No probe at all: the work request is refused before any model call.
    code, value = harness.ask(CALENDAR_QUERY)
    _refused_incompatible(code, value, harness, 0)
    assert value["data"]["feature_support"] == "UNPROBED"
    # 2. A probe whose tools exchange failed leaves tools NOT_VERIFIED and still refuses routing.
    probe_code, probe = harness.probe()
    assert probe["data"]["feature_report"]["features"]["tools"] == "NOT_VERIFIED"
    before = len(script.requests)
    code, value = harness.ask(CALENDAR_QUERY)
    _refused_incompatible(code, value, harness, before)
    assert value["data"]["feature_support"] == "NOT_VERIFIED"
    receipt = receipt_of(value)
    assert receipt["feature_gate"]["tools"] == "NOT_VERIFIED" and receipt["provider_used"] is False


def test_a01_wrong_nonce_and_label_are_not_support(tmp_path, monkeypatch):
    """A completed exchange with the wrong nonce is UNSUPPORTED; a vendor label never sets SUPPORTED.

    Fix round P3: the label is applied before the probe, so the config hash is unchanged between
    probe and ask and the refusal can only come from the measured wrong nonce (not from UNPROBED).
    """
    from s00_t04_support import ScriptedFakeProvider
    monkeypatch.setattr(ScriptedFakeProvider, "supports_tools", True, raising=False)
    monkeypatch.setattr(ScriptedFakeProvider, "default_model", "tool-capable-openai-compatible-1m-context")
    script = Script(probe_tools="wrong")
    harness = Harness(tmp_path, monkeypatch, script)
    harness.install("calendar-read")
    _code, probe = harness.probe()
    assert probe["data"]["feature_report"]["features"]["tools"] == "UNSUPPORTED"
    before = len(script.requests)
    code, value = harness.ask(CALENDAR_QUERY)
    _refused_incompatible(code, value, harness, before)
    assert value["data"]["feature_support"] == "UNSUPPORTED"
    assert receipt_of(value)["feature_gate"]["config_hash"] == probe["data"]["feature_report"]["config_hash"]


def test_a01_report_never_transfers_to_another_config(tmp_path, monkeypatch):
    """M31-FR-02: a SUPPORTED record for config A is not used for config B (different model id)."""
    script = Script()
    harness = Harness(tmp_path, monkeypatch, script)
    harness.install("calendar-read")
    assert harness.probe()[0] == 0
    harness.service.config = ProviderConfig(transport=harness.config.transport, model="fake-model-2",
                                            allow_live=True)
    code, value = harness.ask(CALENDAR_QUERY)
    _refused_incompatible(code, value, harness, len(script.requests))
    assert value["data"]["feature_support"] == "UNPROBED"


def test_a01_stale_or_tampered_report_is_not_current(tmp_path, monkeypatch):
    script = Script()
    harness = Harness(tmp_path, monkeypatch, script)
    harness.install("calendar-read")
    _code, probe = harness.probe()
    harness.clock.advance(ask_module.FEATURE_REPORT_MAX_AGE_S + 1)
    code, value = harness.ask(CALENDAR_QUERY)
    _refused_incompatible(code, value, harness, len(script.requests))
    assert value["data"]["feature_support"] == "STALE"
    harness.clock.advance(-(ask_module.FEATURE_REPORT_MAX_AGE_S + 1))
    path = Path(probe["evidence_refs"][0].split(":", 2)[2])
    tampered = json.loads(path.read_bytes())
    tampered["features"]["tools"] = "SUPPORTED"
    tampered["note"] = "edited"
    path.write_text(json.dumps(tampered))
    code, value = harness.ask(CALENDAR_QUERY)
    _refused_incompatible(code, value, harness, len(script.requests))
    assert value["data"]["feature_support"] == "UNPROBED"


# --------------------------------------------------------------------------- A02
def test_a02(tmp_path, monkeypatch):
    """S00-T04-A02: only a report proven by a nonce round-trip opens dynamic routing.

    Deterministic contribution (L1): the scripted fake echoes the random nonce through the real
    ``Provider.probe``; the report is stored with its config hash and the ask gate accepts it.
    The real-provider round-trip is proven only by tests/external/test_live_claude_cli.py and its
    sanitized evidence (evidence/S00/provider-tdd/live_claude_cli_probe_2026-11-16.json), which this
    test reads but does not re-run.
    """
    script = Script(classified(), search(CALENDAR_QUERY), describe("fixtures.calendar-read"),
                    invoke("fixtures.calendar-read", limit=1), status_of, final("Your next appointment is ready."))
    harness = Harness(tmp_path, monkeypatch, script)
    harness.install("calendar-read")
    code, probe = harness.probe()
    report = probe["data"]["feature_report"]
    assert code == 0 and report["features"]["tools"] == "SUPPORTED"
    assert report["observations"]["tools"] == "PROBE_PASSED"
    assert harness.probe()[1]["data"]["feature_report"]["config_hash"] == report["config_hash"]
    tool_probes = [request for request in script.requests if request.tools]
    nonces = [re.findall(r"[0-9a-f]{32}", request.messages[0].content)[0] for request in tool_probes]
    # S00-T04 fix round 5 (S4, LOG-0032): the probe now measures the real discovery tools (target
    # quati_search) instead of the trivial quati_probe_echo tool; expectation updated.
    assert [request.tools[0].name for request in tool_probes] == ["quati_search"] * 2
    assert len(set(nonces)) == 2                                       # a fresh random nonce per probe
    code, value = harness.ask(CALENDAR_QUERY)
    assert code == 0 and value["status"] == "SUCCEEDED", value
    receipt = receipt_of(value)
    assert receipt["feature_gate"]["tools"] == "SUPPORTED"
    assert receipt["feature_gate"]["config_hash"] == report["config_hash"]
    assert receipt["feature_gate"]["report_ref"].startswith("sha256:")
    live = json.loads((REPOSITORY_ROOT / "evidence/S00/provider-tdd/live_claude_cli_probe_2026-11-16.json").read_text())
    assert (live["transport"], live["features"]["tools"], live["observations"]["tools"]) == (
        "claude_cli", "SUPPORTED", "PROBE_PASSED")


# --------------------------------------------------------------------------- A03
def test_a03(tmp_path, monkeypatch):
    """S00-T04-A03: malformed classification output is bounded: 2 repairs then BLOCKED REPAIR_EXHAUSTED (M17-AT-02)."""
    invalid = ModelResponse(structured={"intent": "make it so"}, model_id="fake-model-1")
    script = Script(invalid, invalid, invalid, final("I did everything"))
    harness = Harness(tmp_path, monkeypatch, script)
    harness.install("calendar-read")
    harness.probe()
    before = len(script.requests)
    code, value = harness.ask(CALENDAR_QUERY)
    assert code == 5
    assert (value["status"], value["error"]["code"], value["data"]["reason"]) == (
        "BLOCKED", "OUTPUT_INVALID", "REPAIR_EXHAUSTED")
    calls = script.requests[before:]
    assert len(calls) == 3                                           # first attempt + exactly two repairs
    assert all(call.output_schema is not None and not call.tools for call in calls)
    assert "SCHEMA_INVALID_OUTPUT" in calls[1].messages[-1].content    # repair carries the validator error only
    assert harness.handlers.total_invocations() == 0
    assert value["data"]["classification"] == {"intent": "professional_work", "work_needed": True,
            "complexity": "investigative", "risk": "high", "uncertainty": "high",
            "safe_work_allowed": False, "next_action": "escalate",
            "reason_code": "CLASSIFICATION_INVALID_ESCALATE"}
    assert value["data"]["classification_stage"] == "FAIL_CLOSED"
    assert len(script.items) == 1                                     # the false "done" reply was never requested


def test_a03_loop_malformed_and_runaway_outputs_are_bounded(tmp_path, monkeypatch):
    """Invalid tool calls get at most two repairs; a runaway model stops at the fixed request budget."""
    bad = tool("quati_delete_everything", target="all")
    script = Script(classified(), bad, bad, bad, final())
    harness = Harness(tmp_path, monkeypatch, script)
    harness.install("calendar-read")
    harness.probe()
    before = len(script.requests)
    code, value = harness.ask(CALENDAR_QUERY)
    assert code == 5 and (value["status"], value["error"]["code"]) == ("BLOCKED", "OUTPUT_INVALID")
    assert value["data"]["reason"] == "REPAIR_EXHAUSTED"
    assert len(script.requests) - before == 4                         # classify + 1 call + 2 repairs
    assert "TOOL_CALL_INVALID" in script.requests[-1].messages[-1].content
    runaway = Script(classified(), *[search(f"appointment {index}") for index in range(20)])
    harness2 = Harness(tmp_path / "second", monkeypatch, runaway)
    harness2.install("calendar-read")
    harness2.probe()
    before = len(runaway.requests)
    code, value = harness2.ask(CALENDAR_QUERY)
    calls = len(runaway.requests) - before
    assert calls <= ask_module.ASK_MAX_PROVIDER_REQUESTS
    assert len(value["data"]["tool_calls"]) <= ask_module.ASK_MAX_TOOL_CALLS
    assert value["status"] != "SUCCEEDED" and code == 4
    assert value["error"]["code"] == "BUDGET_EXCEEDED"
    assert harness2.handlers.total_invocations() == 0


@pytest.mark.parametrize("stop", ["length", "refusal"])
def test_a03_truncated_or_refused_classification_is_repaired_then_blocked(tmp_path, monkeypatch, stop):
    broken = ModelResponse(text="{", stop_reason=stop, model_id="fake-model-1")
    script = Script(broken, broken, broken)
    harness = Harness(tmp_path, monkeypatch, script)
    harness.install("calendar-read")
    harness.probe()
    code, value = harness.ask(CALENDAR_QUERY)
    assert (code, value["data"]["reason"]) == (5, "REPAIR_EXHAUSTED")


# --------------------------------------------------------------------------- A04
def test_a04(tmp_path, monkeypatch):
    """S00-T04-A04: no credential value in prompts, Responses, default receipts or synthetic evidence (M17-RT-02)."""
    canary = "sk-canary-0123456789abcdef"
    # Fix round P3: a distinct canary in variables Quati is NOT configured to use. Redaction only
    # knows the configured reference, so this proves those values never enter any output at all.
    unconfigured = "sk-unconfigured-canary-fedcba9876543210"
    monkeypatch.setenv("QUATI_API_KEY_ENV", "T04_SYNTHETIC_KEY")
    monkeypatch.setenv("T04_SYNTHETIC_KEY", canary)
    for name in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "QUATI_API_KEY"):
        monkeypatch.setenv(name, unconfigured)
    script = Script()
    harness = Harness(tmp_path, monkeypatch, script,
                      config=ProviderConfig(transport="scripted_fake_t04", allow_live=True,
                                            api_key_env="T04_SYNTHETIC_KEY"))
    harness.install("calendar-read")
    _code, probe = harness.probe()
    for synthetic in (False, True):
        script.add(classified(), tool("quati_search", query=f"appointment {canary}"),
                   describe("fixtures.calendar-read"),             # fix round 2 R4: describe before invoke
                   invoke("fixtures.calendar-read", limit=1), status_of, final(f"Done. Key {canary}"))
        code, value = harness.ask(f"{CALENDAR_QUERY} {canary}", synthetic=synthetic)
        assert value["status"] == "SUCCEEDED", value
        for secret in (canary, unconfigured):
            assert secret not in json.dumps(value)
            assert secret.encode() not in receipt_bytes(value)
    for request in script.requests:
        assert canary not in request.system
        visible = (request.system or "") + "".join(message.content for message in request.messages)
        assert unconfigured not in visible
    for secret in (canary, unconfigured):
        assert secret.encode() not in receipt_bytes(probe)
    for path in (tmp_path / "data").rglob("*"):
        if path.is_file():
            data = path.read_bytes()
            assert canary.encode() not in data and unconfigured.encode() not in data, path
