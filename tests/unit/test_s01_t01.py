"""S01-T01 deterministic foundations; contribution proof, never live-model proof."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
import itertools
import json
import math
from pathlib import Path

import jsonschema
import pytest

from quati.application.identity import RequestContext
from quati.behavior.trusted_config import load_decision_policy
from quati.domain.capability_registry import Refusal

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 11, 17, 12, tzinfo=timezone.utc)
BASE = dict(intent='context_lookup', work_needed=True, complexity='short', risk='low',
            uncertainty='low', safe_work_allowed=True, next_action='respond', reason_code='PROPOSAL')
INTENTS = ('social', 'simple_answer', 'status_query', 'context_lookup', 'professional_work',
           'deep_investigation', 'external_action')
COMPLEXITIES = ('trivial', 'short', 'multi_step', 'investigative')
RISKS = ('none', 'low', 'medium', 'high')
EFFECTS = ('none', 'read', 'write', 'dangerous')


def context(**changes):
    values = dict(actor_id='actor-1', tenant_id='tenant-1', space_ids=('space-1',),
                  request_id='request-1', trace_id='trace-1', session_id='auth-session-1',
                  token_jti='token-1', authenticated_origin_ref='fixture:authenticated',
                  deadline_at='2026-11-17T12:01:00+00:00')
    return RequestContext(**(values | changes))


def policy(**changes):
    document = json.loads((ROOT / 'examples/behavior/decision-policy.json').read_text())
    document['routing_policy'].update(changes)
    return load_decision_policy(json.dumps(document).encode())


def test_classification_roundtrip_and_schema_equivalence():
    from quati.domain.classification import RequestClassification
    schema = json.loads((ROOT / 'contracts/request-classification.schema.json').read_text())
    for intent, risk, complexity in itertools.product(INTENTS, RISKS, COMPLEXITIES):
        for extras in ({}, {'commitment_ref': None}, {'commitment_ref': 'opaque-work', 'confidence': 0},
                       {'confidence': 1.0}):
            wire = BASE | dict(intent=intent, risk=risk, complexity=complexity) | extras
            parsed = RequestClassification.from_wire(wire)
            assert parsed.to_wire() == wire
            jsonschema.Draft202012Validator(schema).validate(parsed.to_wire())
            with pytest.raises(FrozenInstanceError):
                parsed.risk = 'none'


def test_classification_rejects_every_missing_or_extra_field_and_bad_type():
    from quati.domain.classification import ClassificationError, RequestClassification
    schema = json.loads((ROOT / 'contracts/request-classification.schema.json').read_text())
    invalid = [None, [], 'social', BASE | {'privilege': 'admin'}, BASE | {'actor_id': 'owner'}]
    invalid += [{key: value for key, value in BASE.items() if key != missing} for missing in BASE]
    for key in ('intent', 'complexity', 'risk', 'uncertainty', 'next_action'):
        invalid += [BASE | {key: value} for value in ('unknown', [], None, 1)]
    for key in ('work_needed', 'safe_work_allowed'):
        invalid += [BASE | {key: value} for value in (0, 1, 'true', None)]
    invalid += [BASE | {'reason_code': value} for value in ('', 'ab', None, 3)]
    invalid += [BASE | {'commitment_ref': value} for value in (3, [], {})]
    invalid += [BASE | {'confidence': value} for value in (-0.01, 1.01, 10 ** 400, True, None, '1')]
    for value in invalid:
        assert not jsonschema.Draft202012Validator(schema).is_valid(value), value
        with pytest.raises(ClassificationError):
            RequestClassification.from_wire(value)
    for value in (math.nan, math.inf, -math.inf):
        with pytest.raises(ClassificationError):
            RequestClassification.from_wire(BASE | {'confidence': value})


def test_route_table_totality_and_trusted_effect_floors():
    from quati.domain.classification import reduce_classification, route_table
    configured = policy()
    seen = set()
    for intent, risk, effect, complexity, uncertainty in itertools.product(
            INTENTS, RISKS, EFFECTS, COMPLEXITIES, ('low', 'medium', 'high')):
        proposal = BASE | dict(intent=intent, risk=risk, complexity=complexity, uncertainty=uncertainty)
        row, action, reason, normalized_effect = route_table(intent, risk, effect, complexity, uncertainty)
        result = reduce_classification(proposal, configured, now=NOW,
                                       proposed_capabilities=('candidate',), effects={'candidate': effect})
        assert result.route_row == row and result.effect_class == normalized_effect
        assert result.classification.next_action == action
        assert row != 'R0' and reason.startswith('ROUTE_')
        seen.add(row)
        if risk == 'high' or normalized_effect in ('write', 'dangerous'):
            assert action in ('ask', 'escalate')
        if risk in ('medium', 'high') or normalized_effect in ('write', 'dangerous'):
            assert result.model_role == 'strong'
        assert result.policy_hash == configured.decision_policy_hash
    assert seen == {f'R{i}' for i in range(1, 10)}
    assert route_table('future_intent', 'low', 'none', 'short', 'low')[:2] == ('R0', 'escalate')
    valid = ['simple_answer', 'low', 'none', 'short', 'low']
    for index in range(len(valid)):
        unknown = valid.copy()
        unknown[index] = 'future_value'
        assert route_table(*unknown)[:2] == ('R0', 'escalate')


def test_restrictive_proposals_unknown_capabilities_and_fail_closed_values():
    from quati.domain.classification import fail_closed, reduce_classification
    configured = policy()
    direct = BASE | dict(intent='simple_answer', work_needed=False, risk='none')
    order = ('respond', 'search_context', 'start_safe_work', 'ask', 'escalate', 'deny')
    for action in order:
        result = reduce_classification(direct | {'next_action': action}, configured, now=NOW)
        assert result.classification.next_action == action
        assert result.classification.reason_code == 'PROPOSAL'
        if action in ('escalate', 'deny'):
            assert result.classification.safe_work_allowed is False
    assert reduce_classification(direct, configured, now=NOW).classification.work_needed is False
    for invalid in (None, BASE | {'intent': 'quick_lookup'}, BASE | {'risk': None}, BASE | {'model_role': 'small'}):
        result = reduce_classification(invalid, configured, now=NOW)
        assert result.classification == fail_closed()
        assert result.model_role == 'strong' and result.priority == 'P0'
    for proposed, registry in ((('unknown',), {}), (('candidate',), {'candidate': 'magic'}), (([],), {})):
        result = reduce_classification(direct, configured, now=NOW,
                                       proposed_capabilities=proposed, effects=registry)
        assert result.effect_class == 'dangerous' and result.classification.next_action == 'escalate'


def test_priority_role_and_deadline_boundaries_use_trusted_policy_and_clock():
    from quati.domain.classification import reduce_classification
    configured = policy()
    for seconds, expected in ((-1, 'P0'), (3600, 'P0'), (3601, 'P1'), (86400, 'P1'), (86401, 'P2')):
        assert reduce_classification(BASE, configured, now=NOW,
                                     deadline_at=NOW + timedelta(seconds=seconds)).priority == expected
    assert reduce_classification(BASE | {'risk': 'high'}, configured, now=NOW).priority == 'P0'
    assert reduce_classification(BASE | {'risk': 'medium', 'work_needed': False}, configured,
                                 now=NOW).classification.work_needed is True
    assert reduce_classification(BASE, configured, now=NOW).model_role == 'small'
    assert reduce_classification(BASE, policy(small_model_max_complexity='trivial'), now=NOW).model_role == 'strong'
    for values in ({'now': NOW.replace(tzinfo=None)}, {'now': 'today'},
                   {'now': NOW, 'deadline_at': NOW.replace(tzinfo=None)}, {'now': NOW, 'deadline_at': 'tomorrow'}):
        with pytest.raises(Refusal) as error:
            reduce_classification(BASE, configured, **values)
        assert error.value.code == 'INVALID_INPUT'
    corrupted = policy()
    corrupted.document['routing_policy']['small_model_max_complexity'] = 'trivial'
    for bad in (None, {}, corrupted):
        with pytest.raises(Refusal) as error:
            reduce_classification(BASE, bad, now=NOW)
        assert error.value.code == 'CONFIG_INVALID'


def test_policy_objects_cannot_bypass_limits_or_schema_field_presence():
    from quati.domain.canonical import digest
    from quati.domain.classification import ClassificationError, RequestClassification, reduce_classification
    from quati.domain.decision_policy import DecisionPolicy
    documents = [{}, [], None]
    for key, value in (('small_model_max_complexity', 'unbounded'), ('small_model_max_complexity', 'multi_step'),
                       ('small_model_max_complexity', 'investigative'), ('urgent_deadline_s', True),
                       ('urgent_deadline_s', -1), ('urgent_deadline_s', 604801)):
        document = policy().document
        section = 'routing_policy' if key == 'small_model_max_complexity' else 'behavior_policy'
        document[section][key] = value
        documents.append(document)
    for document in documents:
        with pytest.raises(Refusal) as error:
            reduce_classification(BASE, DecisionPolicy(document, digest(document)), now=NOW)
        assert error.value.code == 'CONFIG_INVALID'
    parsed = RequestClassification.from_wire(BASE)
    assert reduce_classification(parsed, policy(), now=NOW).classification.intent == BASE['intent']
    with pytest.raises(ClassificationError):
        RequestClassification.from_wire(BASE | {'confidence': parsed.confidence})


def test_direct_context_serializer_matches_the_complete_runtime_schema():
    schema = json.loads((ROOT / 'contracts/runtime-boundaries.schema.json').read_text())
    validator = jsonschema.Draft202012Validator({'$ref': '#/$defs/RequestContext', '$defs': schema['$defs']},
                                               format_checker=jsonschema.FormatChecker())
    for version in (None, 'trusted-policy'):
        wire = context(policy_version=version).to_wire()
        validator.validate(wire)
        assert wire['act'] is None and wire['policy_version'] == version
        assert wire['space_ids'] == ['space-1']


def test_context_policy_version_never_supplies_effect_authority():
    from quati.adapters.policy_gate import LocalPolicyGate
    from quati.application.discovery import build_effect_intent
    from quati.domain.discovery import ScopeGrant
    from quati.domain.policy import KERNEL_BASELINE_VERSION, PolicyState
    directory = type('Directory', (), {'tenant_role': lambda self, ctx: 'OWNER'})()
    gate = LocalPolicyGate(lambda: PolicyState.unavailable('missing'), clock=lambda: NOW,
                           ids=lambda prefix: prefix + '-1', directory=directory)
    outcomes = []
    for version in (None, 'model-supplied-forgery'):
        ctx = context(policy_version=version)
        intent = build_effect_intent(ctx, ScopeGrant(frozenset(), 'space-1'), capability_id='read',
                                     capability_version='1.0.0', binding_id='local', binding_version='1.0.0',
                                     effect_class='read', destinations=(), arguments={}, idempotency_key='key-1',
                                     effect_id='effect-1', policy_version=KERNEL_BASELINE_VERSION)
        assert intent.policy_version == KERNEL_BASELINE_VERSION
        decision = gate.decide(ctx, intent)
        outcomes.append((decision.verdict, decision.reason_code))
    assert outcomes[0] == outcomes[1]
    assert outcomes[0][0] == 'DENY'


def test_projection_is_pure_scoped_and_revision_checked():
    from quati.domain.conversation import ConversationProjection, advance_conversation
    original = ConversationProjection('conversation-1', 'tenant-1', 'actor-1', 2)
    updated = advance_conversation(original, tenant_id='tenant-1', actor_id='actor-1', expected_revision=2)
    assert original.revision == 2 and updated.revision == 3
    for tenant, actor, revision, code in (
            ('tenant-2', 'actor-1', 2, 'FORBIDDEN'), ('tenant-1', 'actor-2', 2, 'FORBIDDEN'),
            ('tenant-1', 'actor-1', 1, 'REVISION_CONFLICT'), ('tenant-1', 'actor-1', True, 'INVALID_INPUT')):
        with pytest.raises(Refusal) as error:
            advance_conversation(original, tenant_id=tenant, actor_id=actor, expected_revision=revision)
        assert error.value.code == code
        assert original.revision == 2
    for args in (('', 'tenant', 'actor', 0), ('id', '', 'actor', 0), ('id', 'tenant', '', 0),
                 ('id', 'tenant', 'actor', -1), ('id', 'tenant', 'actor', True)):
        with pytest.raises(ValueError):
            ConversationProjection(*args)


def test_session_prepares_without_mutation_and_commits_only_its_own_candidate():
    from quati.application.conversation import ConversationSession
    from quati.domain.conversation import ConversationProjection
    session = ConversationSession(ids=lambda prefix: prefix + '-seeded')
    original = {'status': 'SUCCEEDED', 'data': {'text': 'Hello'}, 'evidence_refs': [],
                'error': None, 'uncertainties': [], 'next_action': None}
    candidate, decorated = session.prepare(context(), original)
    assert session.projection is None and 'conversation' not in original['data']
    assert decorated['data']['conversation'] == dict(id='conversation-seeded', revision=1,
                                                     lifetime='PROCESS_ONLY', continues_after_exit=False)
    with pytest.raises(Refusal):
        session.commit(context(), expected_revision=0,
                       candidate=ConversationProjection('forged', 'tenant-1', 'actor-1', 1))
    session.commit(context(), expected_revision=0, candidate=candidate)
    assert session.projection.revision == 1
    for ctx in (context(tenant_id='tenant-2'), context(actor_id='actor-2')):
        with pytest.raises(Refusal) as error:
            session.admit(ctx)
        assert error.value.code == 'FORBIDDEN'
    candidate, _ = session.prepare(context(session_id='new-auth-session'), original)
    assert candidate.id == 'conversation-seeded' and candidate.revision == 2
    session.discard()
    assert session.projection.revision == 1


def test_session_invalid_inputs_and_stale_commits_fail_without_mutation():
    from quati.application.conversation import ConversationSession
    from quati.application.identity import AccessDenied
    from quati.domain.conversation import ConversationProjection
    session = ConversationSession(ids=lambda prefix: prefix + '-seeded')
    for invalid in ({}, context(actor_id=''), context(tenant_id=12)):
        with pytest.raises(AccessDenied):
            session.admit(invalid)
    for invalid in (None, {}, {'data': None}, {'data': []}):
        with pytest.raises(Refusal) as error:
            session.prepare(context(), invalid)
        assert error.value.code == 'INVALID_INPUT' and session.projection is None
    response = {'data': {'text': 'Hello'}, 'status': 'SUCCEEDED'}
    candidate, _ = session.prepare(context(), response)
    for revision, code in ((True, 'INVALID_INPUT'), (-1, 'INVALID_INPUT'), (1, 'REVISION_CONFLICT')):
        with pytest.raises(Refusal) as error:
            session.commit(context(), expected_revision=revision, candidate=candidate)
        assert error.value.code == code and session.projection is None
    with pytest.raises(Refusal) as error:
        session.commit(context(actor_id='other'), expected_revision=0, candidate=candidate)
    assert error.value.code == 'FORBIDDEN'
    session.commit(context(), expected_revision=0, candidate=candidate)
    second, _ = session.prepare(context(), response)
    session.commit(context(), expected_revision=1, candidate=second)
    assert session.projection.revision == 2
    with pytest.raises(Refusal):
        session.commit(context(), expected_revision=2, candidate=second)
    assert session.projection.revision == 2


def test_urgent_policy_minimum_and_maximum_are_not_implicit_defaults():
    from quati.domain.classification import reduce_classification
    from quati.behavior.trusted_config import load_decision_policy
    for urgent in (0, 604800):
        document = policy().document
        document['behavior_policy']['urgent_deadline_s'] = urgent
        configured = load_decision_policy(json.dumps(document).encode())
        at_boundary = reduce_classification(BASE, configured, now=NOW,
                                            deadline_at=NOW + timedelta(seconds=urgent))
        beyond = reduce_classification(BASE, configured, now=NOW,
                                       deadline_at=NOW + timedelta(seconds=urgent + 1))
        assert at_boundary.priority == 'P0'
        assert beyond.priority == ('P1' if urgent < 86400 else 'P2')
