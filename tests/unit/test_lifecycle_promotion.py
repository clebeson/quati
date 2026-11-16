"""REG-04 (RFC-015; M14-FR-03, M14-RT-01, M25-RT-01, K7): agents never enable capabilities."""

from __future__ import annotations

from pathlib import Path

import pytest

from s00_t03_support import AGENT, build, context

from quati.domain.capability_registry import Refusal

REF = "fixtures.forecast-lime@1.0.0"


def test_reg_04(tmp_path: Path) -> None:
    harness = build(tmp_path)
    staged = harness.install("forecast-lime", enable=False)
    assert staged["data"]["lifecycle"] == "STAGED"
    agent = context(actor=AGENT, kind="AGENT")
    before = harness.registry.record(harness.operator, REF)
    with pytest.raises(Refusal) as minted:
        harness.registry.fixture_enable_approval(agent, REF)
    assert minted.value.reason == "ENABLE_REQUIRES_HUMAN_APPROVAL"
    human_approval = harness.registry.fixture_enable_approval(harness.operator, REF)
    for approval in (None, human_approval):
        with pytest.raises(Refusal) as refused:
            harness.registry.transition(agent, REF, before["revision"], "ENABLED", approval=approval)
        assert (refused.value.status, refused.value.reason) == ("DENIED", "ENABLE_REQUIRES_HUMAN_APPROVAL")
    assert harness.registry.record(harness.operator, REF) == before
    # Fault: replay after restart is still denied and the state is unchanged.
    restarted = harness.restart()
    with pytest.raises(Refusal) as replay:
        restarted.registry.transition(agent, REF, before["revision"], "ENABLED", approval=human_approval)
    assert replay.value.reason == "ENABLE_REQUIRES_HUMAN_APPROVAL"
    assert restarted.registry.record(restarted.operator, REF) == before
    assert restarted.turn().search(restarted.operator, "weekly order forecast").data["candidates"] == []
    # Negative: the authorized human promotion succeeds, exactly once.
    enabled = restarted.registry.transition(restarted.operator, REF, before["revision"], "ENABLED",
                                            approval=human_approval)
    assert (enabled["lifecycle"], enabled["enabled_by_approval"]) == ("ENABLED", human_approval.approval_id)
    assert enabled["effect_class_reviewed"] == "read" and enabled["assurance"] == "C2"
    # A replaced binding expires assurance; the consumed approval cannot re-enable it.
    for binding_ref in restarted.registry.binding_refs(restarted.operator, REF):
        restarted.registry.unbind(restarted.operator, binding_ref)
    restarted.registry.bind(restarted.operator, REF,
                            restarted.registry.fixture_binding(REF, "forecast-lime", suffix="b2"))
    staged_again = restarted.registry.transition(
        restarted.operator, REF, restarted.registry.record(restarted.operator, REF)["revision"], "STAGED")
    with pytest.raises(Refusal) as consumed:
        restarted.registry.transition(restarted.operator, REF, staged_again["revision"], "ENABLED",
                                      approval=human_approval)
    assert consumed.value.reason == "ENABLE_REQUIRES_HUMAN_APPROVAL"
    events = [event["event"] for event in restarted.store.audit_events()]
    assert "registry.transition_refused" in events and "registry.transition" in events
