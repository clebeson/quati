"""M31-RT-01 and M31-RT-02 (S00 contribution): competence is never inferred; trimming keeps protected facts."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from s00_t03_support import context  # noqa: E402
from s00_t04_support import CALENDAR_QUERY, FAKE_TRANSPORT, Harness, Script, ScriptedFakeProvider  # noqa: E402
from quati.application import context_envelope as ce  # noqa: E402
from quati.application.ports import ProviderConfig  # noqa: E402


def chars(text: str) -> int:
    return len(text)


def test_large_window_not_competence(tmp_path, monkeypatch):
    """M31-RT-01: an advertised 1M-token window, tool label or parameter count never routes work."""
    monkeypatch.setattr(ScriptedFakeProvider, "context_window_tokens", 1_000_000, raising=False)
    monkeypatch.setattr(ScriptedFakeProvider, "advertised_features", ("tools", "structured_output"), raising=False)
    harness = Harness(tmp_path, monkeypatch, Script(),
                      config=ProviderConfig(transport=FAKE_TRANSPORT, model="huge-window-tools-1m", allow_live=True))
    harness.install("calendar-read")
    code, value = harness.ask(CALENDAR_QUERY)
    assert (code, value["status"], value["data"]["feature_support"]) == (4, "UNAVAILABLE", "UNPROBED")
    assert harness.script.requests == [] and harness.handlers.total_invocations() == 0
    envelope = ce.build_envelope(context(), goal="x", policy_ref="p", stable_text="s", permitted_actions=("respond",))
    assert envelope.budget["max_context_tokens"] == ce.MAX_CONTEXT_TOKENS        # never grown from a claim


def _facts_build(budget, **overrides):
    options = {"goal": "goal", "policy_ref": "trusted_policy/default@" + "a" * 64, "stable_text": "S" * 50,
               "permitted_actions": ("respond",), "work_ref": "work-7", "work_revision": 2, "owner": "agent-1",
               "commitment_state": "ACCEPTED", "recent_turns": [("user", "t" * 20) for _ in range(6)],
               "candidates": [{"capability_id": f"fixtures.c{index}"} for index in range(5)],
               "low_trust": ["L" * 40, "M" * 40], "max_context_tokens": budget, "tokenizer": chars}
    options.update(overrides)
    return ce.build_envelope(context(), **options)


def test_trimming_preserves_protected_facts():
    """M31-RT-02: low-trust first, then older turns, then candidates beyond 2; protected facts never trimmed."""
    full = _facts_build(100_000)
    size = full.budget["used_tokens"]
    trimmed = _facts_build(size - 1)
    assert trimmed.trimmed == ("low_trust",) and trimmed.low_trust == ("M" * 40,)
    no_low_trust = _facts_build(size - 2 * 80)
    assert no_low_trust.low_trust == () and no_low_trust.trimmed[:2] == ("low_trust", "low_trust")
    assert no_low_trust.trimmed[2:] == ("recent_turn",) * (len(no_low_trust.trimmed) - 2)
    floor = _facts_build(100_000, recent_turns=(), low_trust=(), candidates=[]).budget["used_tokens"]
    two = _facts_build(100_000, recent_turns=(), low_trust=(),
                       candidates=[{"capability_id": f"fixtures.c{index}"} for index in range(2)])
    tight = _facts_build(two.budget["used_tokens"])
    assert tight.low_trust == () and tight.recent_turns == ()
    assert [item["capability_id"] for item in tight.candidates] == ["fixtures.c0", "fixtures.c1"]
    assert tight.trimmed[-1] == "candidate"
    for envelope in (trimmed, no_low_trust, tight):
        assert envelope.protected_facts() == full.protected_facts()
        assert envelope.stable_hash() == full.stable_hash()
        assert envelope.budget["used_tokens"] <= envelope.budget["max_context_tokens"]
    with pytest.raises(ce.EnvelopeError) as raised:
        _facts_build(floor - 1, recent_turns=(), low_trust=(), candidates=[])
    assert (raised.value.code, raised.value.reason) == ("BUDGET_EXCEEDED", "CONTEXT_BUDGET_EXCEEDED")
    with pytest.raises(ce.EnvelopeError):
        _facts_build(two.budget["used_tokens"] - 1)   # two candidates are the floor: BUDGET_EXCEEDED
