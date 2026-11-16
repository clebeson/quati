"""M31-FR-01 / M31-AT-02 (S00 contribution): the context envelope builder.

FX-M31-BOUNDARY: a request with 12 recent turns and 9 candidate summaries; deterministic
fake tokenizer (one token per character) so limits are exact.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from s00_t03_support import context  # noqa: E402
from quati.application import context_envelope as ce  # noqa: E402


def chars(text: str) -> int:
    return len(text)


TURNS = [("user" if index % 2 == 0 else "assistant", f"turn {index}") for index in range(12)]
CANDIDATES = [{"capability_id": f"fixtures.c{index}", "rank": index} for index in range(9)]


def build(**overrides):
    options = {"goal": "Find my next appointment", "policy_ref": "trusted_policy/default@" + "a" * 64,
               "stable_text": "Kernel invariants. Role: executive secretary.",
               "permitted_actions": ("respond", "quati_search"), "work_ref": "work-1", "work_revision": 3,
               "owner": "agent-1", "commitment_state": "ACCEPTED", "recent_turns": TURNS, "candidates": CANDIDATES,
               "uncertainties": ("U1",), "evidence_refs": ("sha256:ref",), "tokenizer": chars}
    options.update(overrides)
    return ce.build_envelope(context(), **options)


def test_envelope_fields_and_limits():
    envelope = build()
    document = envelope.to_json()
    assert list(document) == ["schema_version", "goal", "context", "policy_ref", "work_ref", "work_revision",
                              "recent_turns", "evidence_refs", "uncertainties", "permitted_actions", "candidates",
                              "budget"]
    assert document["schema_version"] == ce.SCHEMA_VERSION
    assert len(document["recent_turns"]) == ce.MAX_RECENT_TURNS == 6
    assert document["recent_turns"][-1] == ["assistant", "turn 11"]            # most recent kept
    assert len(document["candidates"]) == ce.MAX_CAPABILITY_CANDIDATES == 5
    assert document["budget"]["used_tokens"] <= document["budget"]["max_context_tokens"] == ce.MAX_CONTEXT_TOKENS
    assert document["budget"]["used_tokens"] == len(envelope.system_text()) + len(envelope.user_text())
    assert envelope.protected_facts() == {"actor_id": context().actor_id, "tenant_id": context().tenant_id,
                                          "work_ref": "work-1", "work_revision": 3, "owner": "agent-1",
                                          "commitment_state": "ACCEPTED"}
    assert "Candidate (untrusted data)" in envelope.user_text()
    assert "Protected facts (trusted)" in envelope.system_text()
    for missing in (None, ""):
        with pytest.raises(ce.EnvelopeError) as raised:
            build(policy_ref=missing)
        assert (raised.value.code, raised.value.reason) == ("INVALID_INPUT", "POLICY_REF_MISSING")
    with pytest.raises(ce.EnvelopeError) as raised:
        build(goal="  ")
    assert raised.value.reason == "GOAL_MISSING"
    with pytest.raises(ce.EnvelopeError) as raised:
        build(permitted_actions=())
    assert raised.value.reason == "PERMITTED_ACTIONS_MISSING"


def test_default_tokenizer_is_a_conservative_byte_estimate():
    assert ce.estimate_tokens("") == 0
    assert ce.estimate_tokens("abc") == 1 and ce.estimate_tokens("abcd") == 2
    assert ce.estimate_tokens("é") == 1                                      # two UTF-8 bytes
    envelope = ce.build_envelope(context(), goal="hello", policy_ref="p", stable_text="s",
                                 permitted_actions=("respond",))
    assert envelope.budget["used_tokens"] == ce.estimate_tokens(envelope.system_text()) + ce.estimate_tokens(
        envelope.user_text())


def test_correction_changes_only_volatile_segment():
    """M31-AT-02: a user correction changes goal/turns/uncertainties only; the stable hash is unchanged."""
    first = build()
    corrected = build(goal="No, I meant my next dentist appointment",
                      recent_turns=[*TURNS, ("user", "No, the dentist one")], uncertainties=("U1", "CORRECTED"))
    assert first.stable_hash() == corrected.stable_hash()
    assert first.stable_segment() == corrected.stable_segment()
    assert first.protected_facts() == corrected.protected_facts()
    assert first.system_text() == corrected.system_text()
    assert first.volatile_segment() != corrected.volatile_segment()
    assert first.envelope_hash() != corrected.envelope_hash()
    changed_policy = build(policy_ref="trusted_policy/default@" + "b" * 64)
    assert changed_policy.stable_hash() != first.stable_hash()
