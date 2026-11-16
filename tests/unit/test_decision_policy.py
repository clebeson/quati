"""Decision-policy sidecar contract (DECISION_RULES section 6, A-13) at the S00-T02 loader.

contracts/decision-policy.schema.json plus the loader-only rules named by the schema:
candidate_score_weights sum to 1 within 1e-9 and replay_retention_s >= signature_tolerance_s.
Every failure is CONFIG_INVALID and the sidecar never grants authority.
"""

from __future__ import annotations

import copy
import json

import pytest

from s00_t02_support import base_decision_policy, base_package, base_machine, mutate
from quati.behavior.compiler import compile_documents
from quati.behavior.trusted_config import load_decision_policy
from quati.domain.canonical import digest
from quati.domain.decision_policy import BLOCKING_FIELDS_MINIMUM, DecisionPolicy, check_decision_policy
from quati.domain.diagnostics import ContractViolation, ErrorCode

FIVE = {"target_resource", "destructive_or_external_effect_confirmation", "recipient",
        "deadline_if_stated_relative_and_unresolvable", "authorization_scope"}


def _load(document) -> DecisionPolicy:
    return load_decision_policy(json.dumps(document).encode())


def _rejected(document) -> ContractViolation:
    with pytest.raises(ContractViolation) as caught:
        _load(document)
    assert caught.value.code is ErrorCode.CONFIG_INVALID
    return caught.value


def test_contract() -> None:
    """The example validates with its exact thresholds; every blocking field is retained."""
    document = base_decision_policy()
    policy = _load(document)
    assert policy.document == document
    assert policy.decision_policy_hash == digest(document)
    assert set(policy.document["behavior_policy"]["blocking_fields"]) == FIVE == set(BLOCKING_FIELDS_MINIMUM)
    behavior = policy.document["behavior_policy"]
    routing = policy.document["routing_policy"]
    assert (behavior["max_open_questions"], behavior["max_reasks_per_field"], behavior["reinvestigation_budget"],
            behavior["max_summary_chars"], behavior["max_delivery_attempts"]) == (1, 1, 2, 1200, 3)
    assert behavior["min_update_interval_s"] == {"local": 60, "channel": 300}
    assert (routing["min_candidate_score"], routing["ambiguity_margin"], routing["max_reference_candidates"]) == (
        0.5, 0.15, 5)
    assert isinstance(policy.document, dict)

    # Removing or replacing a blocking field is rejected (an operator cannot drop one).
    for blocking in (sorted(FIVE)[:4], sorted(FIVE)[:4] + ["nice_to_have"], sorted(FIVE) + ["recipient"]):
        _rejected(mutate(document, "behavior_policy.blocking_fields", blocking))

    # Unknown authority keys are rejected at every level.
    for dotted, value in (("allow_all_effects", True), ("behavior_policy.skip_approval", True),
                          ("routing_policy.trusted_capabilities", ["email.send"]),
                          ("lifecycle_policy.disable_kernel_checks", True)):
        error = _rejected(mutate(document, dotted, value))
        assert error.reason == "SCHEMA_INVALID", dotted

    # Exact thresholds: inside-bound values accepted, one step outside rejected.
    for dotted, low, high in (("behavior_policy.max_open_questions", 1, 5),
                              ("behavior_policy.max_reasks_per_field", 0, 3)):
        _load(mutate(document, dotted, low))
        _load(mutate(document, dotted, high))
        _rejected(mutate(document, dotted, low - 1))
        _rejected(mutate(document, dotted, high + 1))
    _rejected(mutate(document, "schema_version", "decision-policy/2"))
    _rejected(mutate(document, "revision", 0))
    _rejected(mutate(document, "behavior_policy.max_open_questions", True))


def test_candidate_score_weights_sum_to_one() -> None:
    document = base_decision_policy()
    shifted = copy.deepcopy(document)
    shifted["routing_policy"]["candidate_score_weights"]["exact_id"] = 0.36
    assert _rejected(shifted).reason == "WEIGHTS_SUM_INVALID"
    near = copy.deepcopy(document)
    near["routing_policy"]["candidate_score_weights"]["exact_id"] = 0.3500000000001  # within 1e-9
    _load(near)
    far = copy.deepcopy(document)
    far["routing_policy"]["candidate_score_weights"]["exact_id"] = 0.350000002  # outside 1e-9
    assert _rejected(far).reason == "WEIGHTS_SUM_INVALID"


def test_replay_retention_must_cover_signature_tolerance() -> None:
    document = base_decision_policy()
    _load(mutate(document, "channel_policy.replay_retention_s", 300))
    error = _rejected(mutate(document, "channel_policy.replay_retention_s", 299))
    assert error.reason == "REPLAY_RETENTION_TOO_SHORT"
    without_channel = copy.deepcopy(document)
    del without_channel["channel_policy"]
    _load(without_channel)


def test_decision_policy_bytes_are_parsed_strictly() -> None:
    for raw, reason in ((b'{"schema_version": "decision-policy/1", "schema_version": "x"}', "DUPLICATE_KEY"),
                        (b"{", "PARSE_ERROR"), (b"[]", "NOT_A_MAPPING"), (b'{"a": NaN}', "UNSUPPORTED_VALUE")):
        with pytest.raises(ContractViolation) as caught:
            load_decision_policy(raw)
        assert (caught.value.code, caught.value.reason) == (ErrorCode.CONFIG_INVALID, reason)


def test_domain_check_is_independent_of_the_schema_layer() -> None:
    document = base_decision_policy()
    assert check_decision_policy(document).decision_policy_hash == digest(document)
    broken = mutate(document, "behavior_policy.blocking_fields", sorted(FIVE)[:4])
    with pytest.raises(ContractViolation) as caught:
        check_decision_policy(broken)
    assert (caught.value.code, caught.value.reason) == (ErrorCode.CONFIG_INVALID, "BLOCKING_FIELDS_INCOMPLETE")
    for bad in ({}, {"routing_policy": {}}, {"routing_policy": {"candidate_score_weights": {"a": "x"}}},
                {"behavior_policy": {"blocking_fields": list(FIVE)},
                 "routing_policy": {"candidate_score_weights": {"a": 1}}, "channel_policy": "x"}):
        with pytest.raises(ContractViolation) as caught:
            check_decision_policy(bad)
        assert caught.value.code is ErrorCode.CONFIG_INVALID
    with pytest.raises(ContractViolation):
        check_decision_policy(mutate(document, "routing_policy.candidate_score_weights.exact_id", True))


def test_decision_policy_hash_is_bound_into_the_build_digest() -> None:
    first = compile_documents(base_package(), base_machine(), decision_policy=_load(base_decision_policy()))
    plain = compile_documents(base_package(), base_machine())
    changed = compile_documents(base_package(), base_machine(), decision_policy=_load(
        mutate(base_decision_policy(), "behavior_policy.max_open_questions", 2)))
    assert first.receipt == plain.receipt == changed.receipt  # receipt schema has no field for it
    assert first.config_bindings == {"decision_policy_hash": digest(base_decision_policy())}
    assert plain.config_bindings == {}
    assert len({first.build_digest, plain.build_digest, changed.build_digest}) == 3
