"""S00-T04 boundary cases: request budget, feature-report store integrity, gate values, exit tables."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from s00_t04_support import (  # noqa: E402
    CALENDAR_QUERY, SOCIAL, START, Harness, Script, classified, describe, final, invoke, search)
from quati.adapters.feature_reports import FileFeatureReportStore  # noqa: E402
from quati.application import ask as ask_module  # noqa: E402
from quati.application.capability_commands import _exit  # noqa: E402
from quati.application.providers import ModelResponse  # noqa: E402


def ready(tmp_path, monkeypatch, *items):
    harness = Harness(tmp_path, monkeypatch, Script(*items))
    harness.install("calendar-read")
    assert harness.probe()[0] == 0
    harness.base = len(harness.script.requests)
    return harness


def test_social_text_without_an_opening_greeting_gets_no_english_default(tmp_path, monkeypatch):
    """S00-T04 fix round P1-1 (replaces the earlier "defaults to English" expectation): with no template the
    reply is never a fixed "Hello!".

    Fix round 6 (audit F3; S00_RUNTIME_CONTRACT "Independent-review fail-closed refinement"; LOG-0039):
    the expectation changed from the tool-free model reply ("I am well, thank you.") to the
    application-owned no-action notice; no model-written text is displayed in S00."""
    harness = ready(tmp_path, monkeypatch, classified(SOCIAL), final("I am well, thank you."))
    code, value = harness.ask("How are you doing today?")
    assert (code, value["data"]["text"], value["data"]["result_kind"]) == (
        0, ask_module.NO_ACTION_NOTICES["en"], "GREETING")
    assert "I am well" not in json.dumps(value) and value["data"]["text"] != "Hello!"
    assert ask_module.social_reply("How are you doing today?", {"hi": "Hello!"}) is None   # no greeting opens it


def test_model_request_budget_counts_classification_repairs(tmp_path, monkeypatch):
    """Two classification repairs plus loop calls stop at ASK_MAX_PROVIDER_REQUESTS (8) before dispatch."""
    invalid = ModelResponse(structured={"intent": "x"}, model_id="fake-model-1")
    loop = [search(f"appointment {index}") for index in range(4)]
    harness = ready(tmp_path, monkeypatch, invalid, invalid, classified(), search(CALENDAR_QUERY),
                    describe("fixtures.calendar-read"),            # fix round 2 R4: describe before invoke
                    invoke("fixtures.calendar-read", limit=1), *loop)
    code, value = harness.ask(CALENDAR_QUERY)
    assert len(harness.script.requests) - harness.base == ask_module.ASK_MAX_PROVIDER_REQUESTS
    assert code == 0 and value["status"] == "SUCCEEDED"        # the validated invoke stands
    assert "MODEL_LOOP_INCOMPLETE:BUDGET_EXCEEDED" in value["uncertainties"]
    harness2 = ready(tmp_path / "b", monkeypatch, invalid, invalid, classified(),
                     *[search(f"appointment {index}") for index in range(6)])
    code, value = harness2.ask(CALENDAR_QUERY)
    assert (code, value["status"], value["error"]["code"], value["data"]["reason"]) == (
        4, "BLOCKED", "BUDGET_EXCEEDED", "MODEL_REQUEST_BUDGET")


def _sealed(root: Path, document) -> dict:
    raw = (json.dumps(document) if not isinstance(document, bytes) else document.decode()).encode()
    path = root / "receipt.json"
    path.write_bytes(raw)
    return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}


def test_feature_report_store_rejects_bad_keys_and_bodies(tmp_path):
    store = FileFeatureReportStore(tmp_path / "reports")
    report = {"config_hash": "not-a-hash", "transport": "t", "measured_at": START.isoformat()}
    store.save(report, _sealed(tmp_path, report))
    assert not (tmp_path / "reports").exists() and store.load("not-a-hash") is None
    key = "a" * 64
    for body in (b"{not json", json.dumps([1, 2]).encode()):
        receipt = _sealed(tmp_path, body)
        store.save({"config_hash": key, "transport": "t", "measured_at": START.isoformat()}, receipt)
        assert store.load(key) is None
    good = {"kind": "feature_report", "config_hash": key}
    store.save({"config_hash": key, "transport": "t", "measured_at": START.isoformat()}, _sealed(tmp_path, good))
    assert store.load(key)["report"] == good


class _Provider:
    transport = "t"

    def config_hash(self):
        return "b" * 64


@pytest.mark.parametrize(("change", "expected"), [
    ({"kind": "other"}, "UNPROBED"), ({"transport": "u"}, "UNPROBED"), ({"features": None}, "UNPROBED"),
    ({"measured_at": "2026-11-16T12:00:00"}, "UNPROBED"), ({"measured_at": "yesterday"}, "UNPROBED"),
    ({"features": {"tools": "MAYBE"}}, "UNPROBED"), ({"features": {"tools": "UNSUPPORTED"}}, "UNSUPPORTED"),
    ({"measured_at": (START + timedelta(seconds=5)).isoformat()}, "STALE"),
    ({}, "SUPPORTED"),
    ({"observed_model_id": ""}, "NOT_VERIFIED"), ({"observed_model_id": None}, "NOT_VERIFIED"),   # P2-3
    # S00-T04 fix round 5 (S4): only a report measured with the current ask probe profile can be SUPPORTED.
    ({"probe_profile": None}, "NOT_VERIFIED"), ({"probe_profile": {"name": "trivial", "sha256": None}}, "NOT_VERIFIED"),
])
def test_feature_gate_trusts_only_a_matching_current_measurement(tmp_path, change, expected):
    store = FileFeatureReportStore(tmp_path / "reports")
    report = {"kind": "feature_report", "config_hash": "b" * 64, "transport": "t", "measured_at": START.isoformat(),
              "features": {"tools": "SUPPORTED", "structured_output": "NOT_VERIFIED"}, "observed_model_id": "m-1",
              # S00-T04 fix round 5 (S4): the base report now carries the ask probe profile it was measured with.
              "probe_profile": {"name": "ask", "sha256": ask_module.ask_probe_profile().sha256()},
              **change}
    store.save({"config_hash": "b" * 64, "transport": "t", "measured_at": "x"}, _sealed(tmp_path, report))
    gate = ask_module.feature_gate(store, _Provider(), START)
    assert gate["tools"] == expected
    assert ask_module.feature_gate(None, _Provider(), START)["tools"] == "UNPROBED"


@pytest.mark.parametrize(("status", "code", "expected"), [
    ("SUCCEEDED", None, 0), ("PARTIAL", "EVIDENCE_INSUFFICIENT", 0), ("BLOCKED", "INTERNAL_ERROR", 1),
    ("BLOCKED", "INVALID_INPUT", 2), ("BLOCKED", "CONFIG_INVALID", 2), ("BLOCKED", "NOT_CONFIGURED", 3),
    ("UNAVAILABLE", "TEMPORARILY_UNAVAILABLE", 5), ("DENIED", "FORBIDDEN", 4),
])
def test_operator_command_exit_table(status, code, expected):
    assert _exit({"status": status, "error": None if code is None else {"code": code}}) == expected


@pytest.mark.parametrize(("status", "code", "expected"), [
    ("SUCCEEDED", None, 0), ("PARTIAL", "EVIDENCE_INSUFFICIENT", 0), ("BLOCKED", "INTERNAL_ERROR", 1),
    ("BLOCKED", "NOT_CONFIGURED", 3), ("BLOCKED", "OUTPUT_INVALID", 5), ("BLOCKED", "INVALID_INPUT", 4),
    ("DENIED", "FORBIDDEN", 4),
])
def test_ask_exit_table(status, code, expected):
    assert ask_module.exit_code(status, code) == expected
