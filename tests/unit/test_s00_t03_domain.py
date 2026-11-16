"""Pure-domain guards for the S00-T03 registry and discovery (M14-FR-03, M15-FR-02/03, REG-03), L0/L1.

Each test names the guard it discriminates; the public-path behavior is covered by the
REG-* and M14/M15 tests.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from quati.domain.capability_import import mcp_tool_manifest
from quati.domain.capability_registry import (
    Actor, RegistryApproval, RegistryPolicy, Refusal, TransitionFacts, measured_assurance, new_record, parse_ref,
    review_effect, transition_record)
from quati.domain.discovery import (CatalogEntry, ScopeGrant, SearchScope, clamp_limit, filter_reasons,
                                    latest_per_id, query_terms, resolve_choice)

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)
HUMAN = Actor("actor-1", "tenant-1", "HUMAN")
POLICY = RegistryPolicy()


def record(lifecycle="STAGED", assurance="C2", revision=3):
    base = new_record(tenant_id="tenant-1", capability_id="fixtures.x", capability_version="1.0.0",
                      package_sha256="a" * 64, source="fixture:x", import_kind="fixture", now=NOW)
    return {**base, "lifecycle": lifecycle, "assurance": assurance, "revision": revision}


def approval(kind="FIXTURE_ENABLE", effect="read", bindings=("b1",), expires=NOW + timedelta(minutes=15)):
    return RegistryApproval("apr-1", kind, "actor-1", "HUMAN", "tenant-1", "fixtures.x", "1.0.0", bindings, effect,
                            "2026-11-16T12:00:00Z", expires.strftime("%Y-%m-%dT%H:%M:%SZ"))


def facts(**changes):
    values = {"now": NOW, "declared_effect": "read", "binding_ids": ("b1",), "measured": "C2",
              "self_test_evidence": "e" * 64, "fixture_only": True, "approval": approval(), "approval_known": True}
    values.update(changes)
    return TransitionFacts(**values)


def refusal(target, rec=None, actor=HUMAN, **changes):
    rec = rec or record()
    with pytest.raises(Refusal) as raised:
        transition_record(rec, target, expected_revision=rec["revision"], actor=actor, facts=facts(**changes),
                          policy=POLICY)
    return raised.value.reason


def test_parse_ref_accepts_only_registry_ids() -> None:
    assert parse_ref({"id": "fixtures.x", "version": "1.0.0"}) == ("fixtures.x", "1.0.0")
    for bad in ("fixtures.x", "x@1.0.0", "fixtures.x@1.0", 7, {"id": "fixtures.x"}):
        with pytest.raises(Refusal) as raised:
            parse_ref(bad)
        assert raised.value.reason == "NOT_A_CAPABILITY_ID"


def test_measured_assurance_caps_claims() -> None:
    assert measured_assurance("PRODUCTION", True) == "C2"
    assert measured_assurance("CONTRACT", True) == "C1"
    assert measured_assurance("PRODUCTION", False) == "C0"


def test_registry_policy_floor_is_never_lowered() -> None:
    with pytest.raises(ValueError):
        RegistryPolicy(max_effect_class="admin")
    with pytest.raises(ValueError):
        RegistryPolicy(min_enable_assurance="C1")
    assert RegistryPolicy(min_enable_assurance="C3").min_enable_assurance == "C3"


def test_m14_fr_03_transition_guards() -> None:
    assert refusal("ENABLED", rec=record(lifecycle="DRAFT")) == "TRANSITION_NOT_ALLOWED"
    assert refusal("STAGED") == "TRANSITION_NOT_ALLOWED"                     # same state
    assert refusal("DISABLED", actor=Actor("agent", "tenant-1", "AGENT")) == "OPERATOR_REQUIRED"
    assert refusal("ENABLED", actor=Actor("actor-1", "tenant-2", "HUMAN")) == "NOT_A_CAPABILITY_ID"
    staging = record(lifecycle="VALIDATED", assurance="C1")
    assert refusal("STAGED", rec=staging, binding_ids=()) == "BINDING_CHECK_FAILED"
    assert refusal("STAGED", rec=staging, measured="C1") == "ASSURANCE_BELOW_C2"
    assert refusal("ENABLED", approval=approval(bindings=("b2",))) == "ENABLE_REQUIRES_HUMAN_APPROVAL"
    assert refusal("ENABLED", approval=approval(expires=NOW)) == "ENABLE_REQUIRES_HUMAN_APPROVAL"
    assert refusal("ENABLED", approval_consumed=True) == "ENABLE_REQUIRES_HUMAN_APPROVAL"
    assert refusal("ENABLED", approval_known=False) == "ENABLE_REQUIRES_HUMAN_APPROVAL"
    assert refusal("ENABLED", rec=record(assurance="C1")) == "ASSURANCE_BELOW_C2"
    assert refusal("ENABLED", declared_effect="write", approval=approval(effect="write")) == "EFFECT_ABOVE_CEILING"
    assert refusal("ENABLED", fixture_only=False) == "FIXTURE_BINDING_REQUIRED"
    assert refusal("ENABLED", secret_slots=1) == "SECRET_SLOTS_UNRESOLVED"
    with pytest.raises(Refusal) as stale:
        transition_record(record(), "ENABLED", expected_revision=True, actor=HUMAN, facts=facts(), policy=POLICY)
    assert stale.value.reason == "REVISION_CONFLICT"
    enabled = transition_record(record(), "ENABLED", expected_revision=3, actor=HUMAN, facts=facts(), policy=POLICY)
    assert (enabled["lifecycle"], enabled["enabled_by_approval"], enabled["revision"]) == ("ENABLED", "apr-1", 4)
    deprecated = transition_record(enabled, "DEPRECATED", expected_revision=4, actor=HUMAN, facts=facts(),
                                   policy=POLICY)
    assert deprecated["lifecycle"] == "DEPRECATED"


def test_review_effect_guards() -> None:
    rec = record(lifecycle="DRAFT", assurance="C0")
    review = approval(kind="CAPABILITY_REVIEW", effect="read", bindings=())
    for effect, kind_approval in (("admin", review), ("read", approval())):
        with pytest.raises(Refusal) as raised:
            review_effect(rec, effect, expected_revision=3, actor=HUMAN, facts=facts(approval=kind_approval))
        assert raised.value.reason == "REVIEW_REQUIRES_HUMAN_APPROVAL"
    with pytest.raises(Refusal) as stale:
        review_effect(rec, "read", expected_revision=2, actor=HUMAN, facts=facts(approval=review))
    assert stale.value.reason == "REVISION_CONFLICT"


def test_mcp_import_rejects_unusable_tools() -> None:
    intents = {"positive_examples": ["a", "b"], "negative_examples": ["c"]}
    good = {"name": "read_file", "inputSchema": {"type": "object", "properties": {}}}
    for tool, server, version in ((["x"], "io.example", "1.0.0"), ({**good, "name": "Read File"}, "io.example", "1.0.0"),
                                  (good, "io.example", "1.0"), ({**good, "inputSchema": {"type": "string"}},
                                                                "io.example", "1.0.0")):
        with pytest.raises(Refusal) as raised:
            mcp_tool_manifest(tool, server=server, server_version=version, intents=intents)
        assert raised.value.reason == "MCP_TOOL_INVALID"
    manifest, hints, _raw = mcp_tool_manifest({**good, "annotations": "bogus"}, server="io.example",
                                              server_version="1.0.0", intents=intents)
    assert hints == {"mcp_annotations": {}} and manifest["effects"] == "dangerous"


def entry(version="1.0.0", **changes):
    values = {"capability_id": "fixtures.x", "capability_version": version, "lifecycle": "ENABLED", "loadable": True,
              "enforced_effect": "read", "permissions": ("p",), "data_class_ceiling": "PUBLIC",
              "requires_models": (), "bindings_healthy": True, "manifest": {}}
    values.update(changes)
    return CatalogEntry(**values)


def test_m15_fr_02_hard_filters_are_independent_of_text() -> None:
    scope = SearchScope(ScopeGrant(frozenset({"p"}), "space-1"), model_features=frozenset({"tool_calling"}))
    assert filter_reasons(entry(), scope) == ()
    assert filter_reasons(entry(requires_models=("vision",)), scope) == ("MODEL_INCOMPATIBLE",)
    assert filter_reasons(entry(requires_models=("tool_calling",)), scope) == ()
    unknown = SearchScope(ScopeGrant(frozenset({"p"}), "space-1"))
    assert filter_reasons(entry(requires_models=("tool_calling",)), unknown) == ("MODEL_INCOMPATIBLE",)
    capped = SearchScope(ScopeGrant(frozenset({"p"}), "space-1"), cost_cap=1)
    assert filter_reasons(entry(cost_units=2, data_class_ceiling="RESTRICTED", bindings_healthy=False), capped) == (
        "DATA_CLASS_ABOVE_CEILING", "BINDING_UNHEALTHY", "COST_ABOVE_CAP")
    assert [e.capability_version for e in latest_per_id([entry("1.2.0"), entry("1.10.0"), entry("1.3.0")])] == [
        "1.10.0"]
    assert (clamp_limit(None), clamp_limit(True), clamp_limit(0), clamp_limit(3), clamp_limit(50)) == (5, 5, 1, 3, 5)
    assert query_terms("Find MY next appointment, the next one!") == ("find", "next", "appointment", "one")


def test_resolve_choice_cases() -> None:
    shortlist = ("fixtures.a",)
    assert resolve_choice("fixtures.a", shortlist).reason == "TOOL_CALL_MALFORMED"
    assert resolve_choice({"capability_id": "fixtures.a", "arguments": []}, shortlist).verdict == "SELECTION_ERROR"
    assert resolve_choice({"capability_id": "fixtures.b"}, shortlist).reason == "NOT_IN_SHORTLIST"
    assert resolve_choice({"capability_id": "fixtures.a"}, ()).reason == "NO_CANDIDATES"
