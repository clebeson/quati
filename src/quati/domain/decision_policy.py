"""Decision-policy sidecar semantic checks (DECISION_RULES section 6, A-13).

The schema layer (``quati.behavior.trusted_config.load_decision_policy``) validates
``contracts/decision-policy.schema.json`` first; these are the loader-only rules the
schema names. Every failure is ``CONFIG_INVALID``; the sidecar grants no authority.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from decimal import Decimal
from typing import Any, Mapping

from quati.domain.canonical import canonical_bytes, digest
from quati.domain.diagnostics import ErrorCode, violation

BLOCKING_FIELDS_MINIMUM = frozenset({
    "target_resource", "destructive_or_external_effect_confirmation", "recipient",
    "deadline_if_stated_relative_and_unresolvable", "authorization_scope",
})
WEIGHT_TOLERANCE = Decimal("1e-9")


@dataclass(frozen=True)
class DecisionPolicy:
    document: dict
    decision_policy_hash: str


def _section(document: Mapping, name: str, path: str) -> Mapping:
    value = document.get(name)
    if not isinstance(value, Mapping):
        raise violation(ErrorCode.CONFIG_INVALID, "SCHEMA_INVALID", path, f"{path} must be an object")
    return value


def check_decision_policy(document: Any) -> DecisionPolicy:
    if not isinstance(document, Mapping):
        raise violation(ErrorCode.CONFIG_INVALID, "SCHEMA_INVALID", "$", "decision policy must be an object")
    behavior = _section(document, "behavior_policy", "behavior_policy")
    routing = _section(document, "routing_policy", "routing_policy")
    weights = _section(routing, "candidate_score_weights", "routing_policy.candidate_score_weights")

    blocking = behavior.get("blocking_fields")
    if not (isinstance(blocking, list) and len(blocking) == len(BLOCKING_FIELDS_MINIMUM)
            and set(blocking) == BLOCKING_FIELDS_MINIMUM):
        raise violation(ErrorCode.CONFIG_INVALID, "BLOCKING_FIELDS_INCOMPLETE", "behavior_policy.blocking_fields",
                        "blocking_fields must be exactly the five-field minimum set")

    total = Decimal(0)
    for key, weight in weights.items():
        if type(weight) not in (int, float):
            raise violation(ErrorCode.CONFIG_INVALID, "SCHEMA_INVALID",
                            f"routing_policy.candidate_score_weights.{key}", "weight must be a number")
        total += Decimal(str(weight))
    if abs(total - 1) > WEIGHT_TOLERANCE:
        raise violation(ErrorCode.CONFIG_INVALID, "WEIGHTS_SUM_INVALID", "routing_policy.candidate_score_weights",
                        "candidate_score_weights must sum to 1 within 1e-9")

    if "channel_policy" in document:
        channel = _section(document, "channel_policy", "channel_policy")
        retention, tolerance = channel.get("replay_retention_s"), channel.get("signature_tolerance_s")
        if type(retention) is not int or type(tolerance) is not int:
            raise violation(ErrorCode.CONFIG_INVALID, "SCHEMA_INVALID", "channel_policy",
                            "replay_retention_s and signature_tolerance_s must be integers")
        if retention < tolerance:
            raise violation(ErrorCode.CONFIG_INVALID, "REPLAY_RETENTION_TOO_SHORT", "channel_policy.replay_retention_s",
                            "replay_retention_s must be >= signature_tolerance_s")
    return DecisionPolicy(json.loads(canonical_bytes(document)), digest(document))
