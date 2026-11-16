"""S00-T04 public CLI paths: ``quati ask --json [--synthetic-evidence]``, ``quati models probe`` and
``quati capabilities ...`` (M17-AT-01, M17-AT-02, M14-AT-01 contributions).

The operator ``capabilities`` commands run in real child processes (``python -m quati``).
The model is a SCRIPTED FAKE registered in-process for one test only (monkeypatched
provider registry); no child process can select it, because product code never imports
the tests package and an unregistered transport is ``TRANSPORT_UNKNOWN``. Proof tier L1/L2,
never a real-provider proof.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "tests" / "unit"))

from s00_t04_support import (  # noqa: E402
    CALENDAR_QUERY, FAKE_TRANSPORT, FORECAST_QUERY, Script, ScriptedFakeProvider, classified, describe, final,
    invoke, search, status_of)
from quati.adapters import fixture_capabilities as fixtures  # noqa: E402
from quati.application import providers  # noqa: E402
from quati.application.ports import ProviderConfig  # noqa: E402
from quati.application.providers import ModelResponse  # noqa: E402
from quati.cli import main as cli_main  # noqa: E402


class Workspace:
    def __init__(self, root: Path, calls: list) -> None:
        self.root = root
        self.calls = calls


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("QUATI_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("QUATI_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("QUATI_ALLOW_LIVE", raising=False)
    providers.transports()
    monkeypatch.setitem(providers._REGISTRY, FAKE_TRANSPORT, ScriptedFakeProvider)
    monkeypatch.setattr(cli_main, "_config", lambda: ProviderConfig(transport=FAKE_TRANSPORT, allow_live=True))
    calls = []
    for name in ("calendar-read", "forecast-lime", "calendar-write"):
        original = fixtures.FIXTURE_HANDLERS[name]

        def counted(arguments, *, now, _original=original, _name=name):
            calls.append(_name)
            return _original.function(arguments, now=now)
        monkeypatch.setitem(fixtures.FIXTURE_HANDLERS, name, fixtures.FixtureHandler(
            original.name, original.default_capability_id, counted, original.self_test_input, original.evidence_refs))
    return Workspace(tmp_path, calls)


def run_main(capsys, *argv):
    code = cli_main.main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def child(root: Path, *argv: str):
    environment = {"PATH": "/usr/bin:/bin", "PYTHONPATH": str(REPOSITORY_ROOT / "src"), "HOME": str(root),
                   "QUATI_CONFIG_DIR": str(root / "config"), "QUATI_DATA_DIR": str(root / "data")}
    if "COVERAGE_PROCESS_START" in os.environ:          # opt-in subprocess coverage (tests/coverage/sitecustomize.py)
        environment["COVERAGE_PROCESS_START"] = os.environ["COVERAGE_PROCESS_START"]
        environment["PYTHONPATH"] += os.pathsep + str(REPOSITORY_ROOT / "tests" / "coverage")
        if "QUATI_TEST_COVERAGE_LIBRARY" in os.environ:
            environment["QUATI_TEST_COVERAGE_LIBRARY"] = os.environ["QUATI_TEST_COVERAGE_LIBRARY"]
    completed = subprocess.run([sys.executable, "-m", "quati", *argv], capture_output=True, text=True,
                               env=environment, timeout=120)
    return completed.returncode, json.loads(completed.stdout)


def script(monkeypatch, *items, **options) -> Script:
    active = Script(*items, **options)
    monkeypatch.setattr(ScriptedFakeProvider, "active_script", active)
    return active


def receipt(value):
    _, digest, path = value["evidence_refs"][0].split(":", 2)
    raw = Path(path).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest
    return json.loads(raw)


def test_m17_at_01_tool_incompatible_rejected(workspace, monkeypatch, capsys):
    """Tools NOT_VERIFIED: ``quati ask --json`` is UNAVAILABLE UNSUPPORTED MODEL_INCOMPATIBLE, exit 4, no binding call."""
    active = script(monkeypatch, classified(), search(CALENDAR_QUERY), invoke("fixtures.calendar-read", limit=1),
                    final(), probe_tools="fail")
    assert run_main(capsys, "init", "--json")[0] == 0
    assert run_main(capsys, "capabilities", "install-fixture", "calendar-read", "--enable-fixture", "--json")[0] == 0
    workspace.calls.clear()                                          # the install self-test is not an invocation
    code, value = run_main(capsys, "ask", "--json", "--", CALENDAR_QUERY)
    assert (code, value["status"], value["data"]["feature_support"]) == (4, "UNAVAILABLE", "UNPROBED")
    code, probe = run_main(capsys, "models", "probe", "--json")
    assert probe["data"]["feature_report"]["features"]["tools"] == "NOT_VERIFIED"
    before = len(active.requests)
    code, value = run_main(capsys, "ask", "--json", "--", CALENDAR_QUERY)
    assert code == 4 and (value["status"], value["error"]["code"]) == ("UNAVAILABLE", "UNSUPPORTED")
    assert value["data"]["reason"] == "MODEL_INCOMPATIBLE" and value["data"]["feature_support"] == "NOT_VERIFIED"
    assert len(active.requests) == before and workspace.calls == []


def test_m17_at_02_repair_then_blocked(workspace, monkeypatch, capsys):
    """Invalid JSON three times: exactly two repairs, then BLOCKED OUTPUT_INVALID REPAIR_EXHAUSTED; no escalation."""
    invalid = ModelResponse(text="{not json", model_id="fake-model-1")
    active = script(monkeypatch, invalid, invalid, invalid, final("done"))
    run_main(capsys, "init", "--json")
    run_main(capsys, "capabilities", "install-fixture", "calendar-read", "--enable-fixture", "--json")
    workspace.calls.clear()
    assert run_main(capsys, "models", "probe", "--json")[0] == 0
    code, value = run_main(capsys, "ask", "--json", "--synthetic-evidence", "--", CALENDAR_QUERY)
    assert code == 5 and (value["status"], value["error"]["code"], value["data"]["reason"]) == (
        "BLOCKED", "OUTPUT_INVALID", "REPAIR_EXHAUSTED")
    evidence = receipt(value)["synthetic_evidence"]
    assert [call["purpose"] for call in evidence["model_calls"]] == ["classify", "classify_repair", "classify_repair"]
    assert all(call["outcome"] == "OUTPUT_INVALID:SCHEMA_INVALID_OUTPUT" for call in evidence["model_calls"])
    assert evidence["limits"]["max_escalations"] == 0 and evidence["classification"] is None
    assert workspace.calls == [] and len(active.items) == 1


def test_ask_synthetic_evidence_through_the_cli(workspace, monkeypatch, capsys):
    script(monkeypatch, classified(), search(CALENDAR_QUERY), describe("fixtures.calendar-read"),
           invoke("fixtures.calendar-read", limit=1), status_of, final("Done."))
    run_main(capsys, "init", "--json")
    run_main(capsys, "capabilities", "install-fixture", "calendar-read", "--enable-fixture", "--json")
    workspace.calls.clear()
    run_main(capsys, "models", "probe", "--json")
    code, value = run_main(capsys, "ask", "--json", "--synthetic-evidence", "--", CALENDAR_QUERY)
    assert code == 0 and value["data"]["result_kind"] == "FIXTURE_RESULT"
    stored = receipt(value)
    assert stored["synthetic_evidence"]["request_text"] == CALENDAR_QUERY
    assert stored["feature_gate"]["tools"] == "SUPPORTED" and workspace.calls == ["calendar-read"]
    script(monkeypatch, classified(), search(CALENDAR_QUERY), describe("fixtures.calendar-read"),  # fix round 2 R4
           invoke("fixtures.calendar-read", limit=1), final())
    code, value = run_main(capsys, "ask", "--json", "--", CALENDAR_QUERY)
    assert code == 0 and "synthetic_evidence" not in receipt(value)
    assert b"model_visible" not in json.dumps(receipt(value)).encode()   # fix round 2 R5: default stays hash-only


def test_m14_at_01_install_discoverable_after_restart(workspace, monkeypatch, capsys):
    """Operator commands in fresh processes; the new capability is searchable and used without a prompt edit."""
    root = workspace.root
    assert child(root, "init", "--json")[0] == 0
    code, value = child(root, "capabilities", "install-fixture", "calendar-read", "--enable-fixture", "--json")
    assert code == 0 and value["data"]["lifecycle"] == "ENABLED"
    stored = receipt(value)
    assert {event["event"] for event in stored["audit_events"]} >= {"registry.installed", "registry.activation"}
    code, value = child(root, "capabilities", "install-fixture", "forecast-lime", "--json")
    assert code == 0 and value["data"]["lifecycle"] == "STAGED"
    code, value = child(root, "capabilities", "search", "weekly order volume forecast north region", "--json")
    assert "fixtures.forecast-lime" not in [item["capability_id"] for item in value["data"]["candidates"]]
    package = root / "data" / "fixture_sources" / "forecast-lime"
    code, value = child(root, "capabilities", "install", str(package), "--fixture-handler", "forecast-lime",
                        "--enable-fixture", "--json")
    assert code == 0 and value["data"]["already_installed"] is True    # same digest: idempotent, not re-enabled
    assert value["data"]["lifecycle"] == "STAGED"
    code, value = child(root, "capabilities", "install-fixture", "forecast-quick", "--enable-fixture", "--json")
    assert code == 0
    code, value = child(root, "capabilities", "list", "--enabled", "--json")
    assert [item["capability_id"] for item in value["data"]["capabilities"]] == [
        "fixtures.calendar-read", "fixtures.forecast-quick"]
    code, value = child(root, "capabilities", "search", "rough weekly order estimate north region", "--json")
    assert code == 0 and value["data"]["candidates"][0]["capability_id"] == "fixtures.forecast-quick"
    code, value = child(root, "capabilities", "describe", "fixtures.forecast-quick", "--json")
    assert code == 0 and value["data"]["definition"]["input_schema"]["required"] == ["region"]
    # The model path after the restart: a fresh in-process service over the same state.
    script(monkeypatch, classified(), search("rough weekly order estimate north region"),
           describe("fixtures.forecast-quick"),                    # fix round 2 R4: describe before invoke
           invoke("fixtures.forecast-quick", region="north"), final())
    run_main(capsys, "models", "probe", "--json")
    code, value = run_main(capsys, "ask", "--json", "--", "Give me a rough guess of north orders next week")
    assert code == 0 and value["data"]["fixture_results"][0]["capability_id"] == "fixtures.forecast-quick"
    code, value = child(root, "capabilities", "disable", "fixtures.forecast-quick@1.0.0", "--json")
    assert code == 0 and value["data"]["lifecycle"] == "DISABLED"
    assert "registry.transition" in {event["event"] for event in receipt(value)["audit_events"]}
    code, value = child(root, "capabilities", "describe", "fixtures.forecast-quick", "--json")
    assert code == 4 and value["data"]["reason"] == "NOT_ENABLED"
    assert value["next_action"]


def test_operator_command_refusals_are_typed(workspace, capsys):
    root = workspace.root
    child(root, "init", "--json")
    code, value = child(root, "capabilities", "install-fixture", "no-such-fixture", "--json")
    assert (code, value["error"]["code"], value["data"]["reason"]) == (2, "INVALID_INPUT", "FIXTURE_UNKNOWN")
    code, value = child(root, "capabilities", "install-fixture", "calendar-write", "--enable-fixture", "--json")
    assert (code, value["status"], value["data"]["reason"], value["data"]["lifecycle"]) == (
        4, "DENIED", "EFFECT_ABOVE_CEILING", "DRAFT")
    code, value = child(root, "capabilities", "disable", "fixtures.unknown@1.0.0", "--json")
    assert code == 4 and value["status"] in ("DENIED", "BLOCKED")
    code, value = child(root, "capabilities", "install", str(root / "missing"), "--json")
    assert code in (2, 4) and value["status"] == "BLOCKED" and value["next_action"]
    code, value = child(root, "capabilities", "list", "--json")
    assert [item["lifecycle"] for item in value["data"]["capabilities"]] == ["DRAFT"]


# ----------------------------------------------------------------- S00-T04 fix round through the public CLI
def _ready(capsys, *fixture_names):
    run_main(capsys, "init", "--json")
    for name in fixture_names:
        run_main(capsys, "capabilities", "install-fixture", name, "--enable-fixture", "--json")
    assert run_main(capsys, "models", "probe", "--json")[0] == 0


def test_fix_round_partial_no_capability_and_continuation_through_the_cli(workspace, monkeypatch, capsys):
    """P2-2 PARTIAL, L3 NO_CAPABILITY, L2 one continuation and P2-6 timing via ``quati ask --json``."""
    # Fix round 2 R4: describe steps added before each invoke, so the loop has two more calls (was 5).
    script(monkeypatch, classified(), search("calendar appointment event"), describe("fixtures.calendar-read"),
           invoke("fixtures.calendar-read", limit=1), search("create calendar event"),
           describe("fixtures.calendar-write"),
           invoke("fixtures.calendar-write", title="x", start="2026-11-20T10:00:00Z", end="2026-11-20T11:00:00Z"),
           final("Done."))
    _ready(capsys, "calendar-read", "calendar-write")
    workspace.calls.clear()
    code, value = run_main(capsys, "ask", "--json", "--", "Read my next appointment and create an event called x")
    assert (code, value["status"], workspace.calls) == (0, "PARTIAL", ["calendar-read"])
    assert any(note.startswith("STEP_NOT_EXECUTED:") for note in value["uncertainties"])
    assert [call["purpose"] for call in receipt(value)["timing"]["model_calls"]] == ["classify"] + ["loop"] * 7
    script(monkeypatch, classified(), search("translate poem latin"), invoke("NONE_FITS"), final("x"))
    code, value = run_main(capsys, "ask", "--json", "--", "Translate this poem into Latin")
    assert (code, value["status"], value["data"]["result_kind"], value["next_action"]) == (
        0, "SUCCEEDED", "NO_CAPABILITY", "report_no_capability")
    script(monkeypatch, classified(), search(CALENDAR_QUERY), final("Checking..."),
           describe("fixtures.calendar-read"),                     # fix round 2 R4: describe before invoke
           invoke("fixtures.calendar-read", limit=1), final("ok"))
    code, value = run_main(capsys, "ask", "--json", "--synthetic-evidence", "--", CALENDAR_QUERY)
    evidence = receipt(value)["synthetic_evidence"]
    assert (code, value["data"]["result_kind"]) == (0, "FIXTURE_RESULT")
    assert evidence["continuations"] == [{"after_step": 1, "reason": "NO_INVOKE_WITH_SHORTLIST"}]


def test_fix_round_model_identity_gate_through_the_cli(workspace, monkeypatch, capsys):
    """P2-3: a probe that observed no model id never opens routing; a different answering model fails closed."""
    active = script(monkeypatch, classified(), final(), probe_model_id="")
    _ready(capsys, "calendar-read")
    workspace.calls.clear()                                          # the install self-test is not an invocation
    before = len(active.requests)
    code, value = run_main(capsys, "ask", "--json", "--", CALENDAR_QUERY)
    assert (code, value["status"], value["data"]["feature_support"]) == (4, "UNAVAILABLE", "NOT_VERIFIED")
    assert "MODEL_ID_UNOBSERVED" in value["uncertainties"] and len(active.requests) == before
    script(monkeypatch, ModelResponse(structured=dict(classified().structured), model_id="another-model"))
    assert run_main(capsys, "models", "probe", "--json")[0] == 0
    code, value = run_main(capsys, "ask", "--json", "--", CALENDAR_QUERY)
    assert (code, value["data"]["reason"], workspace.calls) == (4, "MODEL_ID_MISMATCH", [])
