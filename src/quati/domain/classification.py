"""Typed request proposals and the pure M08 policy building block (S01-T01).

This reducer grants no authority and dispatches nothing. T02 activates consumption.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
from typing import Mapping, Sequence

from quati.domain.canonical import digest
from quati.domain.capability_registry import Refusal
from quati.domain.decision_policy import DecisionPolicy

INTENTS = ('social', 'simple_answer', 'status_query', 'context_lookup', 'professional_work',
           'deep_investigation', 'external_action')
COMPLEXITIES = ('trivial', 'short', 'multi_step', 'investigative')
RISKS = ('none', 'low', 'medium', 'high')
UNCERTAINTIES = ('low', 'medium', 'high')
ACTIONS = ('respond', 'search_context', 'start_safe_work', 'ask', 'escalate', 'deny')
EFFECTS = ('none', 'read', 'write', 'dangerous')
FLOORS = dict(zip(INTENTS, ('none', 'none', 'none', 'read', 'read', 'read', 'write')))
VOCABULARIES = dict(intent=INTENTS, complexity=COMPLEXITIES, risk=RISKS,
                    uncertainty=UNCERTAINTIES, next_action=ACTIONS)
REQUIRED = tuple(VOCABULARIES) + ('work_needed', 'safe_work_allowed', 'reason_code')
OPTIONAL = ('commitment_ref', 'confidence')


class _Missing(Enum):
    VALUE = 'absent optional field'


class ClassificationError(ValueError):
    """The value is not a request-classification schema instance."""


@dataclass(frozen=True)
class RequestClassification:
    intent: str
    work_needed: bool
    complexity: str
    risk: str
    uncertainty: str
    safe_work_allowed: bool
    next_action: str
    reason_code: str
    commitment_ref: str | None | _Missing = _Missing.VALUE
    confidence: int | float | _Missing = _Missing.VALUE

    def __post_init__(self):
        for name, vocabulary in VOCABULARIES.items():
            value = getattr(self, name)
            if not isinstance(value, str) or value not in vocabulary:
                raise ClassificationError('Classification enum is invalid')
        if type(self.work_needed) is not bool or type(self.safe_work_allowed) is not bool:
            raise ClassificationError('Classification flags must be booleans')
        if not isinstance(self.reason_code, str) or len(self.reason_code) < 3:
            raise ClassificationError('Classification reason code is invalid')
        if (self.commitment_ref is not _Missing.VALUE and self.commitment_ref is not None
                and not isinstance(self.commitment_ref, str)):
            raise ClassificationError('Classification reference is invalid')
        if self.confidence is not _Missing.VALUE:
            # Bounded comparison rejects NaN/infinities without converting large integers.
            if type(self.confidence) not in (int, float) or not 0 <= self.confidence <= 1:
                raise ClassificationError('Classification confidence is invalid')

    @classmethod
    def from_wire(cls, value):
        if (not isinstance(value, dict) or not set(REQUIRED) <= value.keys()
                or not value.keys() <= set(REQUIRED + OPTIONAL)
                or any(item is _Missing.VALUE for item in value.values())):
            raise ClassificationError('Classification fields are invalid')
        return cls(**value)

    def to_wire(self) -> dict:
        return {name: getattr(self, name) for name in REQUIRED + OPTIONAL
                if getattr(self, name) is not _Missing.VALUE}


def fail_closed() -> RequestClassification:
    return RequestClassification('professional_work', True, 'investigative', 'high', 'high', False,
                                 'escalate', 'CLASSIFICATION_INVALID_ESCALATE')


def route_table(intent, risk, effect, complexity, uncertainty) -> tuple[str, str, str, str]:
    """First-match route-table/1, with the intent floor applied before selection."""
    if (intent not in INTENTS or risk not in RISKS or effect not in EFFECTS
            or complexity not in COMPLEXITIES or uncertainty not in UNCERTAINTIES):
        return 'R0', 'escalate', 'ROUTE_DEFAULT_FAIL_CLOSED', 'dangerous'
    effect = max((effect, FLOORS[intent]), key=EFFECTS.index)
    direct = intent in ('social', 'simple_answer')
    rows = (
        ('R1', risk == 'high', 'escalate', 'ROUTE_RISK_HIGH'),
        ('R2', effect == 'dangerous', 'escalate', 'ROUTE_EFFECT_DANGEROUS'),
        ('R3', effect == 'write', 'ask', 'ROUTE_EFFECT_NEEDS_CONFIRMATION'),
        ('R4', direct and uncertainty != 'high' and complexity in ('trivial', 'short'),
         'respond', 'ROUTE_DIRECT_ANSWER'),
        ('R5', intent == 'status_query', 'search_context', 'ROUTE_STATUS_LOOKUP'),
        ('R6', intent == 'context_lookup', 'search_context', 'ROUTE_CONTEXT_LOOKUP'),
        ('R7', intent == 'simple_answer' and complexity in ('multi_step', 'investigative'),
         'start_safe_work', 'ROUTE_SIMPLE_BUT_NONTRIVIAL'),
        ('R8', direct, 'search_context', 'ROUTE_UNCERTAIN_SHORT_REQUEST'),
        ('R9', True, 'start_safe_work', 'ROUTE_SAFE_WORK'),
    )
    row, _matches, action, reason = next(row for row in rows if row[1])
    return row, action, reason, effect


@dataclass(frozen=True)
class PolicyRoute:
    classification: RequestClassification
    effect_class: str
    route_row: str
    model_role: str
    priority: str
    policy_hash: str


def _policy_limits(policy):
    try:
        if not isinstance(policy, DecisionPolicy) or digest(policy.document) != policy.decision_policy_hash:
            raise ValueError('Unbound policy')
        threshold = policy.document['routing_policy']['small_model_max_complexity']
        urgent = policy.document['behavior_policy']['urgent_deadline_s']
        if threshold not in ('trivial', 'short') or type(urgent) is not int or not 0 <= urgent <= 604800:
            raise ValueError('Invalid policy limits')
        return threshold, urgent
    except (KeyError, TypeError, ValueError) as exc:
        raise Refusal('BLOCKED', 'CONFIG_INVALID', 'DECISION_POLICY_INVALID') from exc


def _aware(instant):
    if not isinstance(instant, datetime) or instant.utcoffset() is None:
        raise Refusal('BLOCKED', 'INVALID_INPUT', 'TRIAGE_TIME_INVALID')


def _effect(intent: str, proposed: Sequence[str], effects: Mapping[str, str]) -> str:
    observed = [FLOORS[intent]]
    for capability in proposed:
        effect = effects.get(capability) if isinstance(capability, str) else None
        observed.append(effect if effect in EFFECTS else 'dangerous')
    return max(observed, key=EFFECTS.index)


def _proposed_role(classification, effect, cutoff):
    small = (classification.risk in ('none', 'low') and classification.uncertainty != 'high'
             and COMPLEXITIES.index(classification.complexity) <= COMPLEXITIES.index(cutoff)
             and effect in ('none', 'read'))
    return 'small' if small else 'strong'


def _priority(classification, now, deadline_at, urgent):
    remaining = None if deadline_at is None else (deadline_at - now).total_seconds()
    if classification.risk == 'high' or (remaining is not None and remaining <= urgent):
        return 'P0'
    if remaining is not None and remaining <= 86400:
        return 'P1'
    return 'P2' if classification.work_needed else 'P3'


def reduce_classification(proposal, policy, *, now, deadline_at=None,
                          proposed_capabilities=(), effects=None) -> PolicyRoute:
    """Normalize a proposal with trusted inputs; this does not activate a route."""
    threshold, urgent = _policy_limits(policy)
    _aware(now)
    if deadline_at is not None:
        _aware(deadline_at)
    if proposed_capabilities is None:
        raise Refusal('BLOCKED', 'INVALID_INPUT', 'TRIAGE_CAPABILITIES_INVALID')
    try:
        parsed = proposal if isinstance(proposal, RequestClassification) else RequestClassification.from_wire(proposal)
    except ClassificationError:
        parsed = fail_closed()
    effect = _effect(parsed.intent, proposed_capabilities, effects or {})
    row, action, reason, effect = route_table(parsed.intent, parsed.risk, effect,
                                              parsed.complexity, parsed.uncertainty)
    if ACTIONS.index(action) <= ACTIONS.index(parsed.next_action):
        action, reason = parsed.next_action, parsed.reason_code
    nontrivial = (parsed.complexity in ('multi_step', 'investigative')
                  or parsed.intent in ('professional_work', 'deep_investigation', 'external_action')
                  or parsed.risk in ('medium', 'high'))
    published = replace(parsed, next_action=action, reason_code=reason,
                        work_needed=parsed.work_needed or nontrivial,
                        safe_work_allowed=(parsed.safe_work_allowed and effect in ('none', 'read')
                                           and parsed.risk != 'high' and action not in ('escalate', 'deny')))
    return PolicyRoute(published, effect, row, _proposed_role(published, effect, threshold),
                       _priority(published, now, deadline_at, urgent), policy.decision_policy_hash)
