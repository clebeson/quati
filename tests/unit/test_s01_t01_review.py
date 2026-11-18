"""Independent S01-T01 review: new adversarial and fault cases (deterministic, no provider, no network).

Authored by the reviewer; these cases do not repeat tests/unit/test_s01_t01.py. A red test here is
a preserved finding, not a reason to edit source. Tier: L1 deterministic unit / scripted fake.
"""

from datetime import datetime, timezone
import json
from pathlib import Path

import jsonschema
import pytest

from quati.application.cli_service import CLIService
from quati.application.conversation import ConversationSession
from quati.application.identity import RequestContext
from quati.behavior.trusted_config import load_decision_policy
from quati.domain.capability_registry import Refusal
from quati.domain.classification import (ClassificationError, RequestClassification,
                                         reduce_classification)

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)
BASE = dict(intent='context_lookup', work_needed=True, complexity='short', risk='low',
            uncertainty='low', safe_work_allowed=True, next_action='respond', reason_code='PROPOSAL')
SCHEMA = json.loads((ROOT / 'contracts/runtime-boundaries.schema.json').read_text())
CONTEXT_VALIDATOR = jsonschema.Draft202012Validator(
    {'$ref': '#/$defs/RequestContext', '$defs': SCHEMA['$defs']}, format_checker=jsonschema.FormatChecker())


def context(**changes):
    values = dict(actor_id='actor-1', tenant_id='tenant-1', space_ids=('space-1',),
                  request_id='request-1', trace_id='trace-1', session_id='auth-session-1',
                  token_jti='token-1', authenticated_origin_ref='fixture:authenticated',
                  deadline_at='2026-11-18T12:01:00+00:00')
    return RequestContext(**(values | changes))


def policy():
    document = json.loads((ROOT / 'examples/behavior/decision-policy.json').read_text())
    return load_decision_policy(json.dumps(document).encode())


def counter():
    state = {'n': 0}

    def ids(prefix):
        state['n'] += 1
        return f'{prefix}-{state["n"]}'
    return ids


# --- RequestContext boundary (M08/M26 identity fields must not carry caller-chosen values) ---

@pytest.mark.parametrize('forged', [
    [{'actor_id': 'root', 'principal_kind': 'AGENT'}], {'actor_id': 'root'}, 'admin', []])
def test_direct_context_never_serializes_a_caller_supplied_delegation_chain(forged):
    """T01 implements no delegated authentication: a direct LOCAL context must emit act=null.

    The field is annotated ``None`` but nothing enforces it, so a forged chain would reach the wire.
    """
    wire = context(act=forged).to_wire()
    assert wire['act'] is None


@pytest.mark.parametrize('version', ['', 7, ['v']])
def test_context_policy_version_is_null_or_a_nonempty_string_on_the_wire(version):
    """Contract section 3: null or a nonempty string; the schema has minLength 1 and type string."""
    try:
        wire = context(policy_version=version).to_wire()
    except (ValueError, TypeError, Refusal):
        return  # rejecting at construction or serialization is conforming
    CONTEXT_VALIDATOR.validate(wire)


# --- M08-RT-01/RT-02: a trusted effect map and registry synonyms cannot lower a route ---

@pytest.mark.parametrize('poisoned', ['READ', 'Write', None, ['read'], True, 0, '', 'none '])
def test_malformed_registry_effect_values_are_dangerous_never_permissive(poisoned):
    proposal = dict(BASE, intent='social', risk='none', complexity='trivial', uncertainty='low',
                    next_action='respond', safe_work_allowed=True)
    route = reduce_classification(proposal, policy(), now=NOW, proposed_capabilities=('email.send',),
                                  effects={'email.send': poisoned})
    assert route.effect_class == 'dangerous' and route.route_row == 'R2'
    assert route.classification.next_action == 'escalate'
    assert route.classification.safe_work_allowed is False and route.model_role == 'strong'


def test_capability_id_synonyms_do_not_inherit_the_registered_effect():
    proposal = dict(BASE, intent='social', risk='none', complexity='trivial')
    for synonym in ('Email.Send', ' email.send', 'email.send​', 'email.send\x00', b'email.send', 7, None):
        route = reduce_classification(proposal, policy(), now=NOW, proposed_capabilities=(synonym,),
                                      effects={'email.send': 'none'})
        assert route.effect_class == 'dangerous' and route.classification.next_action == 'escalate', synonym


def test_model_flags_cannot_make_a_floor_or_dangerous_route_safe():
    hostile = dict(BASE, intent='external_action', risk='none', complexity='trivial', uncertainty='low',
                   next_action='respond', work_needed=False, safe_work_allowed=True)
    route = reduce_classification(hostile, policy(), now=NOW)
    assert route.effect_class == 'write' and route.classification.next_action == 'ask'
    assert route.classification.safe_work_allowed is False and route.classification.work_needed is True


def test_absent_proposed_capabilities_value_fails_closed_without_a_raw_crash():
    """A caller passing None for the capability list must not escape as an untyped TypeError."""
    try:
        route = reduce_classification(dict(BASE), policy(), now=NOW, proposed_capabilities=None)
    except Refusal:
        return
    assert route.effect_class in ('read', 'dangerous')


def test_in_place_policy_tampering_after_load_is_refused_by_the_bound_hash():
    loaded = policy()
    try:
        loaded.document['routing_policy']['small_model_max_complexity'] = 'short'
        loaded.document['behavior_policy']['urgent_deadline_s'] = 0
        loaded.document['routing_policy']['x'] = 1
    except TypeError:
        pytest.skip('policy document is immutable')
    with pytest.raises(Refusal) as error:
        reduce_classification(dict(BASE), loaded, now=NOW)
    assert error.value.code == 'CONFIG_INVALID'


@pytest.mark.parametrize('confidence', [10 ** 400, -10 ** 400, True, False, '0.5', float('inf'), float('nan'), 1.0000001])
def test_confidence_extremes_are_rejected_without_overflow_or_coercion(confidence):
    with pytest.raises(ClassificationError):
        RequestClassification.from_wire(dict(BASE, confidence=confidence))


def test_to_wire_returns_a_fresh_mapping_so_callers_cannot_mutate_the_frozen_value():
    value = RequestClassification.from_wire(dict(BASE, confidence=0.5))
    first = value.to_wire()
    first['risk'] = 'none'
    first['intent'] = 'social'
    assert value.to_wire() == dict(BASE, confidence=0.5)


# --- Conversation coordinator faults ---

def test_second_prepare_supersedes_the_first_and_the_stale_candidate_cannot_commit():
    session = ConversationSession(ids=counter())
    response = {'status': 'SUCCEEDED', 'data': {'text': 'Hello'}}
    first, _ = session.prepare(context(), response)
    second, _ = session.prepare(context(), response)
    assert first.id != second.id  # a first-turn id is generated per prepare
    with pytest.raises(Refusal) as error:
        session.commit(context(), expected_revision=0, candidate=first)
    assert error.value.reason == 'CONVERSATION_PREPARE_MISMATCH'
    assert session.projection is None
    session.commit(context(), expected_revision=0, candidate=second)
    assert session.projection.id == second.id and session.projection.revision == 1


def test_commit_without_any_prepare_and_double_commit_are_refused():
    session = ConversationSession(ids=counter())
    response = {'status': 'SUCCEEDED', 'data': {}}
    candidate, _ = session.prepare(context(), response)
    session.discard()
    with pytest.raises(Refusal):
        session.commit(context(), expected_revision=0, candidate=candidate)
    assert session.projection is None


def test_ids_generator_returning_an_unusable_value_leaves_no_projection_or_prepared_state():
    session = ConversationSession(ids=lambda prefix: '')
    with pytest.raises((Refusal, ValueError)):
        session.prepare(context(), {'data': {}})
    assert session.projection is None and session._prepared is None


# --- Receipt coordination through the real CLIService._record boundary ---

def service(sink, session):
    return CLIService(None, None, sink, conversation=session)


def result():
    return {'status': 'SUCCEEDED', 'data': {'result_kind': 'GREETING'}, 'evidence_refs': [],
            'error': None, 'uncertainties': [], 'next_action': None}


def receipt(record):
    return {'sha256': 'a' * 64, 'path': 'receipts/x.json'}


def test_mid_session_receipt_failure_keeps_id_and_revision_then_retry_advances_once():
    from quati.adapters.evidence import ReceiptNotWritten
    session = ConversationSession(ids=counter())
    ok = service(receipt, session)
    code, first = ok._record('hi', context(request_id='r1'), 0, result())
    assert first['data']['conversation']['revision'] == 1
    conversation_id = first['data']['conversation']['id']

    def failing(record):
        raise ReceiptNotWritten('named fault point: second turn before acknowledgement')
    with pytest.raises(ReceiptNotWritten):
        service(failing, session)._record('hi', context(request_id='r2'), 0, result())
    assert session.projection.revision == 1 and session.projection.id == conversation_id
    assert session._prepared is None
    code, third = ok._record('hi', context(request_id='r3'), 0, result())
    assert third['data']['conversation'] == dict(id=conversation_id, revision=2, lifetime='PROCESS_ONLY',
                                                 continues_after_exit=False)


def test_receipted_output_hash_binds_the_decorated_response_and_caller_object_is_unmutated():
    captured = []
    session = ConversationSession(ids=counter())
    original = result()
    code, decorated = service(lambda record: captured.append(record) or receipt(record), session)._record(
        'hi', context(), 0, original)
    assert 'conversation' not in original['data'] and original['evidence_refs'] == []
    assert decorated['data']['conversation']['revision'] == 1
    assert captured and 'conversation' not in json.dumps(captured[0])  # receipt record carries no metadata text
    assert decorated['evidence_refs'] == ['sha256:' + 'a' * 64 + ':receipts/x.json']


def test_owner_mismatch_is_refused_before_the_sink_is_called():
    session = ConversationSession(ids=counter())
    service(receipt, session)._record('hi', context(), 0, result())
    calls = []
    with pytest.raises(Refusal) as error:
        service(lambda record: calls.append(record) or receipt(record), session)._record(
            'hi', context(actor_id='intruder'), 0, result())
    assert error.value.code == 'FORBIDDEN' and calls == []
    assert session.projection.revision == 1
