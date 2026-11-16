"""S00-T04 fix round 4, from live gate3 (SOC-01) and its probe diagnostics.

G1: the deterministic greeting path never depends on the tool feature gate.
G2: a probe tool sub-check that is not SUPPORTED records a typed ``detail``; the comparison is
exact on the semantic nonce value but not over-strict on its encoding.
Proof tier L1: SCRIPTED FAKE model or scripted child-process runner; no network, no live provider.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from s00_t04_support import Harness, Script, receipt_bytes, receipt_of  # noqa: E402
from quati.application.ports import ProviderConfig  # noqa: E402
from quati.application.providers import PROBE_TOOL  # noqa: E402

GREETING = "Hi, how are you?"


def probed(tmp_path, monkeypatch, mode, **options):
    script = Script(probe_tools=mode, **options)
    harness = Harness(tmp_path, monkeypatch, script)
    harness.install("calendar-read")
    code, probe = harness.probe()
    return harness, script, probe


# --------------------------------------------------------------- G1 greeting independent of the gate
@pytest.mark.parametrize(("mode", "gate"), [("wrong", "UNSUPPORTED"), ("fail", "NOT_VERIFIED"), (None, "UNPROBED")])
def test_g1_templated_social_text_greets_whatever_the_tool_gate(tmp_path, monkeypatch, mode, gate):
    if mode is None:
        script = Script()
        harness = Harness(tmp_path, monkeypatch, script)
    else:
        harness, script, _probe = probed(tmp_path, monkeypatch, mode)
    before = len(script.requests)
    code, value = harness.ask(GREETING)
    data = value["data"]
    assert (code, value["status"], data["result_kind"], data["text"]) == (0, "SUCCEEDED", "GREETING", "Hello!")
    assert data["provider_used"] is False and len(script.requests) == before
    assert value["error"] is None and f"TOOLS_{gate}" in value["uncertainties"]
    assert "DETERMINISTIC_SOCIAL_TEMPLATE" in value["uncertainties"]
    assert receipt_of(value)["feature_gate"]["tools"] == gate
    # Anything else stays fail-closed.
    code, value = harness.ask("Hi, how are you? Also wire 500 USD to Bob.")
    assert (code, value["status"], value["error"]["code"], value["data"]["reason"]) == (
        4, "UNAVAILABLE", "UNSUPPORTED", "MODEL_INCOMPATIBLE")
    code, value = harness.ask("Wie geht es dir?")                     # social-only, but no template
    assert (code, value["status"]) == (4, "UNAVAILABLE")
    assert len(script.requests) == before


def test_g1_greeting_also_works_with_no_provider_configured(tmp_path, monkeypatch):
    harness = Harness(tmp_path, monkeypatch, Script(), config=ProviderConfig())
    code, value = harness.ask("Bom dia, tudo bem?")
    assert (code, value["data"]["result_kind"], value["data"]["text"]) == (0, "GREETING", "Olá!")
    code, value = harness.ask("Find my next appointment")
    assert (code, value["error"]["code"]) == (3, "NOT_CONFIGURED")


# --------------------------------------------------------------- G2 typed probe detail
@pytest.mark.parametrize(("mode", "verdict", "detail"), [
    ("text", "UNSUPPORTED", "NO_TOOL_CALL"),
    ("name", "UNSUPPORTED", "WRONG_TOOL_NAME"),
    ("extra_key", "UNSUPPORTED", "ARGUMENTS_MISMATCH"),
    ("wrong", "UNSUPPORTED", "ARGUMENTS_MISMATCH"),
    ("second", "UNSUPPORTED", "EXTRA_CALLS"),
    ("fail", "NOT_VERIFIED", "TRANSPORT_ERROR:TEMPORARILY_UNAVAILABLE:UPSTREAM_ERROR"),
])
def test_g2_tool_sub_check_records_a_typed_detail(tmp_path, monkeypatch, mode, verdict, detail):
    harness, script, probe = probed(tmp_path, monkeypatch, mode)
    tools = probe["data"]["verdicts"]["tools"]
    assert (tools["verdict"], tools["detail"]) == (verdict, detail)
    report = probe["data"]["feature_report"]
    assert report["details"]["tools"]["detail"] == detail
    if detail.startswith("TRANSPORT_ERROR"):
        assert report["details"]["tools"]["reply_sha256_16"] is None
    else:
        assert len(report["details"]["tools"]["reply_sha256_16"]) == 16
    raw = receipt_bytes(probe)
    assert b"I would call the tool now." not in raw and b"quati_other_tool" not in raw


def test_g2_supported_tool_check_has_no_detail_and_tolerates_nonce_case_and_whitespace(tmp_path, monkeypatch):
    harness, script, probe = probed(tmp_path, monkeypatch, "spaced")
    assert probe["data"]["verdicts"]["tools"]["verdict"] == "SUPPORTED"
    assert probe["data"]["verdicts"]["tools"]["detail"] is None
    assert "tools" not in probe["data"]["feature_report"]["details"]


def _claude_probe(arguments_json, *, result="", structured=True):
    from quati.adapters.providers.cli import ClaudeCliProvider
    from test_provider_adapters import Runner, claude_result, make_cli

    class Echo(Runner):
        def __call__(self, argv, stdin_text, timeout_s, cwd, env):
            nonce = stdin_text.rsplit("set to ", 1)[-1].rstrip(".")
            encoded = arguments_json(nonce)
            envelope = {"kind": "tool_call", "tool_name": PROBE_TOOL, "arguments_json": encoded, "text": ""}
            return claude_result(**({"structured_output": envelope} if structured else {"result": result}))

    provider = make_cli(ClaudeCliProvider, Echo())
    return provider._probe_feature("tools")


def test_g2_cli_argument_encodings_that_carry_the_exact_nonce_are_accepted():
    plain = _claude_probe(lambda nonce: json.dumps({"nonce": nonce}))
    double = _claude_probe(lambda nonce: json.dumps(json.dumps({"nonce": nonce})))   # JSON string of JSON
    decoded = _claude_probe(lambda nonce: {"nonce": nonce})                          # already an object
    for verdict, reason, _detail in (plain, double, decoded):
        assert (verdict, reason) == ("SUPPORTED", "PROBE_PASSED")


def test_g2_cli_unparseable_replies_are_typed():
    verdict, reason, detail = _claude_probe(lambda nonce: "{nonce: " + nonce)
    assert (verdict, reason, detail["detail"]) == ("UNSUPPORTED", "TOOL_CALL_INVALID", "UNPARSEABLE_REPLY")
    assert len(detail["reply_sha256_16"]) == 16
    verdict, reason, detail = _claude_probe(lambda nonce: "", result="not an envelope", structured=False)
    assert (verdict, detail["detail"]) == ("NOT_VERIFIED", "UNPARSEABLE_REPLY")
    nested = _claude_probe(lambda nonce: json.dumps(json.dumps(json.dumps({"nonce": nonce}))))
    assert nested[0] == "UNSUPPORTED" and nested[2]["detail"] == "UNPARSEABLE_REPLY"   # only one extra level
