"""Deterministic tests of the live-evaluation oracle (tests/evals/live_harness.py).

Risk boundary: S00-GATE-02 grading must not be lenient (TEST_CASES CAP-01/CAP-02, M15-RT-01; M26-AT-01
for the CAP-02 explanation; CAP-03 L3; third audit findings X7 H5 and X17 H7 of LOG-0044).
These run on synthetic receipts only; they spend nothing and prove nothing about a provider.
"""
import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'evals'))
import live_harness as h  # noqa: E402

TARGET = 'fixtures.forecast-lime'
ARGS = {'region': 'north', 'horizon_weeks': 2}


def _receipt(trajectory=None, system='Use the tools.', request='Forecast north for two weeks.'):
    trajectory = trajectory if trajectory is not None else [
        {'tool_name': 'quati_search', 'arguments': {'query': 'forecast'}, 'candidate_ids': [TARGET],
         'presented_order': [TARGET], 'handler_executed': False},
        {'tool_name': 'quati_describe', 'arguments': {'capability_id': TARGET}, 'handler_executed': False},
        {'tool_name': 'quati_invoke', 'arguments': {'capability_id': TARGET, 'input': dict(ARGS)},
         'handler_executed': True}]
    return {'synthetic_evidence': {
        'trajectory': trajectory, 'outcome': {'executed_capabilities': [TARGET + '@1.0.0']},
        'provider': {'observed_model_ids': ['m-1']},
        'model_calls': [{'index': 1, 'model_visible': {'system': system, 'transport_rendering': {'system': system},
                                                        'messages': [{'role': 'user', 'content': request}]}}]}}


def _value():
    return {'status': 'SUCCEEDED', 'error': None,
            'data': {'result_kind': 'FIXTURE_RESULT',
                     'fixture_results': [{'outcome_verification': 'VERIFIED', 'label': 'FIXTURE_RESULT'}]}}


def _grade(receipt):
    return h.grade_selection(_value(), receipt, 'forecast-lime', ['forecast-quick', 'forecast-publish'], ARGS)


def test_clean_trajectory_passes():
    assert _grade(_receipt())['pass']


def _failed_selection(receipt=None, value=None, arguments=ARGS, forbidden=('forecast-quick', 'forecast-publish')):
    graded = h.grade_selection(value or _value(), receipt or _receipt(), 'forecast-lime', list(forbidden), arguments)
    return sorted(name for name, ok in graded['checks'].items() if not ok)


def test_selection_rules_each_catch_their_violation():
    extra = _receipt()
    extra['synthetic_evidence']['trajectory'].append(
        {'tool_name': 'quati_invoke', 'arguments': {'capability_id': 'fixtures.calendar-read', 'input': {}}, 'handler_executed': True})
    assert _failed_selection(extra) == ['every_invoke_attempt_is_target', 'only_target_executed']
    anonymous = _receipt()
    anonymous['synthetic_evidence']['provider'] = {'observed_model_ids': []}
    assert _failed_selection(anonymous) == ['provider_identity_recorded']
    del anonymous['synthetic_evidence']['provider']
    assert _failed_selection(anonymous) == ['provider_identity_recorded']
    late = _receipt()
    late['synthetic_evidence']['trajectory'].reverse()
    assert 'search_before_invoke' in _failed_selection(late) and 'describe_before_invoke' in _failed_selection(late)
    other = _receipt()
    other['synthetic_evidence']['outcome'] = {'executed_capabilities': ['fixtures.forecast-quick@1.0.0']}
    assert _failed_selection(other) == ['outcome_executed_matches']
    unverified = _value()
    unverified['data']['fixture_results'][0]['outcome_verification'] = 'UNVERIFIED'
    assert _failed_selection(value=unverified) == ['fixture_result_verified']
    blocked = _value()
    blocked.update(status='BLOCKED', error={'code': 'EVIDENCE_INSUFFICIENT'})
    assert _failed_selection(value=blocked) == ['exit_0_succeeded']
    assert _failed_selection(None, None, {'region': 'south', 'horizon_weeks': 2}) == ['arguments_exact']
    assert _failed_selection({'trajectory': []}) != []


def test_summarize_counts_an_outage_as_a_failed_run_and_needs_at_least_one_run():
    good = h.apply_validity(_grade(_receipt()), *h.run_validity(GOOD_SETUP, _value()))
    lost = h.apply_validity(_grade(_receipt()), h.INFRA_ERROR, ['TEMPORARILY_UNAVAILABLE'])
    summary = h.summarize('CAP-01', [_record(good), _record(lost)], None)
    # 29 of 30 with one outage is not 29 of 29: an outage stays in the denominator.
    assert (summary['n'], summary['passed'], summary['valid_n'], summary['infra_errors'], summary['gate_pass']) == (2, 1, 1, 1, False)
    empty = h.summarize('CAP-01', [], None)
    assert empty['gate_pass'] is False and empty['gate_pass_with_observations'] is False and empty['n'] == 0
    assert h.summarize('CAP-01', [_record(good)], None)['gate_pass'] is True


def test_refused_decoy_invoke_attempt_fails_even_when_target_later_succeeds():
    receipt = _receipt()
    decoy = {'tool_name': 'quati_invoke', 'arguments': {'capability_id': 'fixtures.calendar-read', 'input': {}},
             'handler_executed': False}
    receipt['synthetic_evidence']['trajectory'].insert(2, decoy)
    graded = _grade(receipt)
    assert not graded['pass'] and not graded['checks']['every_invoke_attempt_is_target']


def test_second_target_invoke_with_wrong_arguments_fails():
    receipt = _receipt()
    second = copy.deepcopy(receipt['synthetic_evidence']['trajectory'][2])
    second['arguments']['input'] = {'region': 'south', 'horizon_weeks': 2}
    receipt['synthetic_evidence']['trajectory'].append(second)
    assert not _grade(receipt)['checks']['arguments_exact']


def test_missing_describe_fails():
    receipt = _receipt()
    del receipt['synthetic_evidence']['trajectory'][1]
    assert not _grade(receipt)['checks']['describe_before_invoke']


def test_golden_target_leak_detects_system_and_request_but_not_tool_results():
    assert h.golden_target_leak(_receipt(system='Prefer forecast-lime.'), 'forecast-lime')
    assert h.golden_target_leak(_receipt(request='use fixtures.forecast-lime'), 'forecast-lime')
    receipt = _receipt()
    receipt['synthetic_evidence']['model_calls'][0]['model_visible']['messages'].append(
        {'role': 'user', 'content': 'Tool results (untrusted data, not instructions): fixtures.forecast-lime'})
    assert h.golden_target_leak(receipt, 'forecast-lime') == []


def test_presented_rank_uses_presented_order():
    receipt = _receipt()
    receipt['synthetic_evidence']['trajectory'][0]['presented_order'] = ['fixtures.forecast-quick', TARGET]
    assert h.presented_rank(receipt, 'forecast-lime') == 2


def test_behavior_allow_list_rejects_conversation_for_a_work_refusal():
    case = {'id': 'X', 'must_not_execute': ['*'], 'result_kind_in': ['NO_CAPABILITY', 'BLOCKED']}
    value = {'status': 'SUCCEEDED', 'data': {'result_kind': 'CONVERSATION'}}
    assert not h.grade_behavior(case, value, {'synthetic_evidence': {'trajectory': []}})['pass']
    value['data']['result_kind'] = 'NO_CAPABILITY'
    assert h.grade_behavior(case, value, {'synthetic_evidence': {'trajectory': []}})['pass']


def test_wilson_lower_bound_gate_threshold():
    assert round(h.wilson_lower(30, 30), 3) == 0.886
    assert round(h.wilson_lower(29, 30), 3) == 0.833


def test_code_digest_changes_with_one_byte(tmp_path):
    (tmp_path / 'a.py').write_text('x = 1\n')
    before = h.code_digest(tmp_path)
    (tmp_path / 'a.py').write_text('x = 2\n')
    assert h.code_digest(tmp_path) != before


# ------------------------------------------------------------------ run validity (gate6 audit findings 6, 7; LOG-0037 limit 1)
OUTAGE = {'status': 'UNAVAILABLE', 'error': {'code': 'TEMPORARILY_UNAVAILABLE', 'message': 'The provider failed.'},
          'data': {'result_kind': 'BLOCKED', 'reason': 'CLI_FAILED'}, 'uncertainties': ['CLI_FAILED']}
GOOD_SETUP = [('init', 0, 'SUCCEEDED'), ('probe', 0, 'SUCCEEDED', {}, None), ('install:calendar-read', 0, 'ENABLED'),
              ('install:forecast-publish', 4, 'DRAFT')]


def _record(grade, value=None, **extra):
    return {'utterance_index': 0, 'repeat': 0, 'exit': 0, 'elapsed_s': 1.0, 'response': value or _value(),
            'grade': grade, **extra}


def test_outage_response_passes_a_behavior_case_vacuously_but_is_an_infra_error():
    # BEH-10 of the gate6 run: "must not execute anything" is true when the provider never answered.
    case = {'id': 'BEH-10', 'must_not_execute': ['*'], 'status_not': ['SUCCEEDED']}
    graded = h.grade_behavior(case, OUTAGE, None)
    assert graded['pass']
    h.apply_validity(graded, *h.run_validity(GOOD_SETUP, OUTAGE))
    assert graded['validity'] == h.INFRA_ERROR and graded['pass'] is False and graded['invalid_case'] == h.INFRA_ERROR
    summary = h.summarize('BEHAVIOR', [_record(graded, OUTAGE)], None)
    assert (summary['passed'], summary['infra_errors'], summary['valid_n'], summary['gate_pass']) == (0, 1, 0, False)


def test_infra_error_is_only_the_outage_codes():
    assert h.infra_error(OUTAGE) == 'TEMPORARILY_UNAVAILABLE'
    assert h.infra_error({'status': 'BLOCKED', 'error': {'code': 'EVIDENCE_INSUFFICIENT'}, 'data': {'reason': 'CLI_FAILED'}}) == 'CLI_FAILED'
    assert h.infra_error({'status': 'BLOCKED', 'error': {'code': 'EVIDENCE_INSUFFICIENT'},
                          'data': {'reason': 'NO_VERIFIED_EXECUTION'}}) is None
    assert h.infra_error(_value()) is None


def test_valid_run_keeps_its_grade_and_a_pass_is_counted():
    graded = h.apply_validity(_grade(_receipt()), *h.run_validity(GOOD_SETUP, _value()))
    assert graded['validity'] == h.VALID and graded['pass']
    summary = h.summarize('CAP-01', [_record(graded)], None)
    assert (summary['passed'], summary['valid_n'], summary['gate_pass']) == (1, 1, True)


def test_unexpected_write_distractor_install_is_invalid_setup_and_fails_the_case():
    # The refusal (exit 4, never ENABLED) is the expected result; any other result invalidates the run.
    for bad in (('install:forecast-publish', 0, 'ENABLED'), ('install:forecast-publish', 0, 'DRAFT'),
                ('install:forecast-publish', 4, 'ENABLED'), ('install:forecast-publish', 1, None)):
        steps = GOOD_SETUP[:3] + [bad]
        assert h.setup_violations(steps), bad
        graded = h.apply_validity(_grade(_receipt()), *h.run_validity(steps, _value()))
        assert graded['validity'] == h.INVALID_SETUP and graded['pass'] is False
    summary = h.summarize('CAP-01', [_record(graded)], None)
    assert (summary['passed'], summary['invalid_setup'], summary['gate_pass']) == (0, 1, False)
    assert summary['failures'][0]['validity'] == h.INVALID_SETUP


def test_failed_read_install_init_or_probe_is_a_setup_violation():
    assert h.setup_violations(GOOD_SETUP) == []
    assert h.setup_violations([('init', 1, None)])
    assert h.setup_violations([('install:calendar-read', 0, 'STAGED')])
    assert h.setup_violations([('install:calendar-read', 4, 'ENABLED')])
    assert h.setup_violations([('disable:forecast-lime', 4, 'DENIED')])
    lost = [('init', 0, 'SUCCEEDED'), ('probe', 5, 'UNAVAILABLE', None, 'TEMPORARILY_UNAVAILABLE')]
    assert h.run_validity(lost, _value())[0] == h.INFRA_ERROR
    refused = [('init', 0, 'SUCCEEDED'), ('probe', 3, 'BLOCKED', None, 'NOT_CONFIGURED')]
    assert h.run_validity(refused, _value())[0] == h.INVALID_SETUP


def test_staged_write_option_has_its_own_expected_setup_result():
    staged = [('install:calendar-write', 0, 'STAGED')]
    assert h.setup_violations(staged)
    assert h.setup_violations(staged, write_exit=0, write_lifecycles={'STAGED'}) == []
    assert h.setup_violations([('install:calendar-write', 0, 'ENABLED')], write_exit=0, write_lifecycles={'STAGED'})


def test_unparseable_stdout_is_never_a_pass():
    case = {'id': 'X', 'must_not_execute': ['*']}
    value = {'unparseable_stdout': 'Traceback'}
    graded = h.apply_validity(h.grade_behavior(case, value, None), *h.run_validity(GOOD_SETUP, value))
    assert graded['validity'] == h.INVALID_RESPONSE and graded['pass'] is False


# ------------------------------------------------------------------ M26-AT-01 observation (decision D6)
class _Profile:
    def __init__(self, code, value):
        self.answer, self.calls = (code, value, 0.0), []

    def cli(self, *arguments):
        self.calls.append(arguments)
        return self.answer


def test_trace_explain_unsupported_is_a_failed_check_not_a_skip():
    unsupported = {'status': 'UNAVAILABLE', 'error': {'code': 'UNSUPPORTED', 'message': 'S02'}, 'data': {}}
    profile = _Profile(4, unsupported)
    observed = h.trace_explain(profile, 'request-1', TARGET)
    assert profile.calls == [('trace', 'explain', 'request-1', '--json')]
    assert observed['pass'] is False and observed['checks']['trace_explain_available'] is False
    assert observed['error_code'] == 'UNSUPPORTED'
    invalid = {'status': 'DENIED', 'error': {'code': 'INVALID_INPUT', 'message': 'x'}, 'data': None}
    assert h.trace_explain(_Profile(2, invalid), 'request-1', TARGET)['pass'] is False
    assert h.trace_explain(_Profile(0, {}), None, TARGET)['checks'] == {'request_id_present': False}


def _candidate(capability_id, authorization='ALLOW', excluded_reason=None, reasons=()):
    return {'capability_id': capability_id, 'version': '1.0.0', 'authorization': authorization,
            'excluded_reason': excluded_reason, 'filter_reasons': list(reasons),
            'rank_features': {'rank': 1} if excluded_reason is None else None}


def _explained(target=TARGET):
    """`data` of `quati trace explain` in the S00 form (docs/prds/M26.md, "S00 form of show and explain")."""
    return {'status': 'SUCCEEDED', 'error': None, 'data': {
        'selected': {'capability_id': target, 'version': '1.0.0', 'binding_hash': 'b' * 64},
        'candidates': sorted([_candidate(target),
                              _candidate('fixtures.calendar-write', 'DENY', 'scope_not_granted', ['NOT_AUTHORIZED']),
                              _candidate('fixtures.zz-decoy', 'ALLOW', 'outcome_mismatch')],
                             key=lambda item: item['capability_id']),
        'executed_capabilities': [f'{target}@1.0.0'], 'policy_decision_id': 'decision-1', 'model_rationale': None,
        'observed_model_ids': ['m-1'], 'model_id': 'm-1'}, 'uncertainties': []}


def test_trace_explain_passes_only_on_the_recorded_explanation_shape():
    observed = h.trace_explain(_Profile(0, _explained()), 'request-1', TARGET)
    assert observed['pass'] is True and set(observed['checks']) == {
        'request_id_present', 'trace_explain_available', 'explain_catalog_was_recorded', 'explain_selected_is_target',
        'explain_selected_bound_to_allow_decision', 'explain_executed_is_target',
        'explain_target_candidate_not_excluded', 'explain_target_carries_rank_features',
        'explain_alternatives_carry_reasons', 'explain_write_alternatives_denied',
        'explain_candidates_sorted_and_unique', 'explain_model_identity_recorded', 'explain_no_model_text'}
    assert observed['listed_candidates'] == {TARGET: None, 'fixtures.calendar-write': 'scope_not_granted',
                                             'fixtures.zz-decoy': 'outcome_mismatch'}
    # The earlier check ("the target id appears somewhere in data") accepted this answer: the id is only an
    # excluded alternative and another capability was selected.
    other = _explained('fixtures.mail-search')
    other['data']['candidates'].append(_candidate(TARGET, 'ALLOW', 'lower_rank'))
    other['data']['candidates'].sort(key=lambda item: item['capability_id'])
    failed = h.trace_explain(_Profile(0, other), 'request-1', TARGET)
    assert sorted(name for name, ok in failed['checks'].items() if not ok) == [
        'explain_alternatives_carry_reasons',     # the capability selected instead carries no excluded reason
        'explain_executed_is_target', 'explain_selected_is_target', 'explain_target_candidate_not_excluded',
        'explain_target_carries_rank_features']    # an excluded candidate carries no rank features
    guessed = {'status': 'SUCCEEDED', 'error': None, 'data': {'selected_capability': TARGET, 'candidates': []}}
    assert h.trace_explain(_Profile(0, guessed), 'request-1', TARGET)['pass'] is False


EXPLAIN_MUTATIONS = {
    'explain_selected_is_target': lambda d: d['selected'].update(capability_id='fixtures.calendar-write'),
    'explain_selected_bound_to_allow_decision': lambda d: d.update(policy_decision_id=None),
    'explain_executed_is_target': lambda d: d['executed_capabilities'].append('fixtures.zz-decoy@1.0.0'),
    'explain_target_candidate_not_excluded': lambda d: next(
        item for item in d['candidates'] if item['capability_id'] == TARGET).update(excluded_reason='lower_rank'),
    'explain_alternatives_carry_reasons': lambda d: d['candidates'][-1].update(excluded_reason=None),
    'explain_write_alternatives_denied': lambda d: next(
        item for item in d['candidates'] if item['capability_id'] == 'fixtures.calendar-write').update(
            authorization='ALLOW', excluded_reason='lower_rank'),
    'explain_candidates_sorted_and_unique': lambda d: d['candidates'].reverse(),
    'explain_no_model_text': lambda d: d.update(model_rationale='I chose the calendar.'),
    'explain_target_carries_rank_features': lambda d: next(
        item for item in d['candidates'] if item['capability_id'] == TARGET).update(rank_features=None),
    'explain_model_identity_recorded': lambda d: d.update(observed_model_ids=[]),
}


@pytest.mark.parametrize('rule', sorted(EXPLAIN_MUTATIONS))
def test_trace_explain_each_rule_is_the_only_one_that_catches_its_violation(rule):
    explained = _explained()
    EXPLAIN_MUTATIONS[rule](explained['data'])
    observed = h.trace_explain(_Profile(0, explained), 'request-1', TARGET)
    assert sorted(name for name, ok in observed['checks'].items() if not ok) == [rule]


CAL_READ, CAL_WRITE, MAIL = 'fixtures.calendar-read', 'fixtures.calendar-write', 'fixtures.mail-search'


def _cap02_explained():
    """The explanation the M26-AT-01 oracle describes for CAP-02 (FX-CONFUSABLE-CAPS)."""
    explained = _explained(CAL_READ)
    explained['data']['candidates'] = [_candidate(CAL_READ), _candidate(CAL_WRITE, 'DENY', 'scope_not_granted', ['NOT_AUTHORIZED']),
                                       _candidate(MAIL, 'ALLOW', 'outcome_mismatch')]
    return explained


def _cap02_failed(explained):
    observed = h.trace_explain(_Profile(0, explained), 'request-1', CAL_READ, h.CAP02_ALTERNATIVES)
    return sorted(name for name, ok in observed['checks'].items() if not ok)


def test_h5_cap02_explanation_must_list_the_alternatives_the_oracle_names_with_their_reasons():
    assert h.CAP02_ALTERNATIVES == {CAL_WRITE: ('DENY', 'scope_not_granted'), MAIL: ('ALLOW', 'outcome_mismatch')}
    assert _cap02_failed(_cap02_explained()) == []
    # Audit 3 finding H5: an explanation with no alternative at all passed.
    alone = _cap02_explained()
    alone['data']['candidates'] = [_candidate(CAL_READ)]
    assert _cap02_failed(alone) == ['explain_lists_the_oracle_alternatives']
    assert all(h.explanation_checks(alone['data'], CAL_READ).values())           # what the old check saw
    for missing in (CAL_WRITE, MAIL):
        one = _cap02_explained()
        one['data']['candidates'] = [item for item in one['data']['candidates'] if item['capability_id'] != missing]
        assert _cap02_failed(one) == ['explain_lists_the_oracle_alternatives'], missing
    # Listed, with a reason of the M26 table that is not the oracle's (the audit's second record).
    ranked = _cap02_explained()
    ranked['data']['candidates'][2].update(excluded_reason='lower_rank')
    assert _cap02_failed(ranked) == ['explain_oracle_alternatives_have_the_oracle_reasons']
    policy = _cap02_explained()
    policy['data']['candidates'][1].update(excluded_reason='policy_denied')
    assert _cap02_failed(policy) == ['explain_oracle_alternatives_have_the_oracle_reasons']
    denied = _cap02_explained()
    denied['data']['candidates'][2].update(authorization='DENY')
    assert _cap02_failed(denied) == ['explain_oracle_alternatives_have_the_oracle_reasons']
    # No oracle given (another case): the two rules are not part of the check; an empty oracle is never a pass.
    assert 'explain_lists_the_oracle_alternatives' not in h.explanation_checks(_cap02_explained()['data'], CAL_READ)
    assert h.explanation_checks(_cap02_explained()['data'], CAL_READ, {})['explain_lists_the_oracle_alternatives'] is False


def test_h5_explanation_built_without_the_recorded_catalog_is_not_complete():
    partial = _cap02_explained()
    partial['uncertainties'] = [h.UNRANKED_UNCERTAINTY]
    assert _cap02_failed(partial) == ['explain_catalog_was_recorded']


# ------------------------------------------------------------------ CAP-03 L3 (audit 3 finding H7)
DISABLED = 'fixtures.forecast-lime'


def _disabled(status='UNAVAILABLE', code='UNSUPPORTED', kind='NO_CAPABILITY', reason='NO_CANDIDATES', steps=None, exit_code=4):
    """The model searched, the disabled capability was excluded with NOT_ENABLED, nothing ran."""
    search = {'tool_name': 'quati_search', 'arguments': {'query': 'forecast'}, 'handler_executed': False,
              'candidate_ids': [], 'excluded': [{'capability_id': DISABLED, 'reasons': ['NOT_ENABLED']}]}
    value = {'status': status, 'error': {'code': code, 'message': 'x'} if code else None,
             'data': {'result_kind': kind, 'reason': reason, 'provider_used': True, 'launched': False}}
    return exit_code, value, {'synthetic_evidence': {'trajectory': [search] if steps is None else steps}}


def _invoke_step(capability_id, executed, reason=None):
    return {'tool_name': 'quati_invoke', 'arguments': {'capability_id': capability_id, 'input': {}},
            'handler_executed': executed, 'reason': reason}


def _disabled_failed(code, value, receipt):
    graded = h.grade_disabled(code, value, receipt, DISABLED)
    return sorted(name for name, ok in graded['checks'].items() if not ok)


@pytest.mark.parametrize('status,code', [('UNAVAILABLE', 'UNSUPPORTED'), ('BLOCKED', 'EVIDENCE_INSUFFICIENT'), ('DENIED', 'NOT_FOUND')])
def test_h7_cap03_passes_on_the_honest_outcomes_of_the_product(status, code):
    graded = h.grade_disabled(*_disabled(status, code), DISABLED)                   # decision D7, any typed status
    assert graded['pass'] and graded['outcome_class'] == 'NO_CAPABILITY'
    assert (graded['status'], graded['error_code']) == (status, code) and graded['guard'] == {
        'excluded_by_search': True, 'invoke_refused': False}
    refused = _disabled('DENIED', 'FORBIDDEN', 'BLOCKED', 'NOT_IN_SHORTLIST',
                        steps=[_invoke_step(DISABLED, False, 'NOT_IN_SHORTLIST')])
    graded = h.grade_disabled(*refused, DISABLED)
    assert graded['pass'] and graded['outcome_class'] == 'INVOKE_REFUSED' and graded['guard']['invoke_refused'] is True
    answered = h.grade_disabled(*_disabled('BLOCKED', 'EVIDENCE_INSUFFICIENT', 'BLOCKED', 'NO_VERIFIED_EXECUTION'), DISABLED)
    assert answered['pass'] and answered['outcome_class'] == 'ANSWER_BLOCKED'


def test_h7_cap03_any_other_non_success_fails():
    # The audit's record: the ask is refused for an unrelated reason, exit 2, with zero model calls.
    unrelated = (2, {'status': 'BLOCKED', 'data': {}, 'error': {'code': 'CONFIG_INVALID'}}, None)
    assert _disabled_failed(*unrelated) == ['exit_4', 'guard_observed_on_the_disabled_capability', 'launched_false',
                                            'model_was_asked', 'typed_non_success_of_the_product']
    code, value, receipt = _disabled('UNAVAILABLE', 'UNSUPPORTED', 'BLOCKED', 'MODEL_INCOMPATIBLE')
    assert _disabled_failed(code, value, receipt) == ['typed_non_success_of_the_product']
    code, value, receipt = _disabled(status='PARTIAL', exit_code=4)
    assert _disabled_failed(code, value, receipt) == ['typed_non_success_of_the_product']
    assert _disabled_failed(*_disabled(exit_code=5)) == ['exit_4']
    assert _disabled_failed(*_disabled(exit_code=0)) == ['exit_4']
    # A refused invoke needs its error code; the D2 block needs its own.
    assert _disabled_failed(*_disabled('DENIED', None, 'BLOCKED', 'NOT_IN_SHORTLIST')) == ['typed_non_success_of_the_product']
    assert _disabled_failed(*_disabled('BLOCKED', 'FORBIDDEN', 'BLOCKED', 'NO_VERIFIED_EXECUTION')) == [
        'typed_non_success_of_the_product']


def test_h7_cap03_needs_the_model_the_guard_and_no_execution():
    code, value, receipt = _disabled()
    value['data']['provider_used'] = False
    assert _disabled_failed(code, value, receipt) == ['model_was_asked']
    # The model never looked: nothing shows the guard refusing the disabled capability.
    blind = _disabled('BLOCKED', 'EVIDENCE_INSUFFICIENT', 'BLOCKED', 'NO_VERIFIED_EXECUTION', steps=[
        {'tool_name': 'quati_search', 'arguments': {}, 'handler_executed': False, 'excluded': []}])
    assert _disabled_failed(*blind) == ['guard_observed_on_the_disabled_capability']
    other_reason = _disabled(steps=[{'tool_name': 'quati_search', 'handler_executed': False,
                                     'excluded': [{'capability_id': DISABLED, 'reasons': ['EFFECT_ABOVE_CEILING']}]}])
    assert _disabled_failed(*other_reason) == ['guard_observed_on_the_disabled_capability']
    other_capability = _disabled(steps=[{'tool_name': 'quati_search', 'handler_executed': False,
                                         'excluded': [{'capability_id': 'fixtures.calendar-write', 'reasons': ['NOT_ENABLED']}]}])
    assert _disabled_failed(*other_capability) == ['guard_observed_on_the_disabled_capability']
    code, value, receipt = _disabled()
    receipt['synthetic_evidence']['trajectory'].append(_invoke_step(DISABLED, True))
    assert _disabled_failed(code, value, receipt) == ['disabled_not_executed']
    code, value, receipt = _disabled()
    receipt['synthetic_evidence']['trajectory'].append(_invoke_step('fixtures.calendar-read', True))
    assert _disabled_failed(code, value, receipt) == ['no_other_capability_executed']
    code, value, receipt = _disabled()
    value['data']['launched'] = True
    assert _disabled_failed(code, value, receipt) == ['launched_false']
    # A false success: SUCCEEDED, exit 0, whatever the rest says.
    code, value, receipt = _disabled(status='SUCCEEDED', code=None, exit_code=0)
    assert _disabled_failed(code, value, receipt) == ['not_succeeded']


def test_h7_run_disabled_case_fails_on_an_invalid_run_and_on_a_failed_disable(monkeypatch, tmp_path):
    answers = {'disable': (0, {'status': 'SUCCEEDED'}, 0.0), 'ask': _disabled()}

    class Fake:
        log, root = [], tmp_path

        def cli(self, *arguments, **options):
            if arguments[0] == 'ask':
                code, value, _ = answers['ask']
                return code, value, 0.0
            return answers['disable']
    monkeypatch.setattr(h, 'setup_profile', lambda *a, **k: (Fake(), list(GOOD_SETUP)))
    monkeypatch.setattr(h, 'receipt_of', lambda value: answers['ask'][2])
    monkeypatch.setattr(h, 'profile_cost', lambda profile: {})
    result = h.run_disabled_case(tmp_path, 't', 'm', 1)
    assert result['pass'] is True and result['failed_checks'] == [] and result['outcome_class'] == 'NO_CAPABILITY'
    assert (result['response_status'], result['error_code'], result['exit']) == ('UNAVAILABLE', 'UNSUPPORTED', 4)
    answers['disable'] = (4, {'status': 'DENIED'}, 0.0)
    assert h.run_disabled_case(tmp_path, 't', 'm', 1)['failed_checks'] == ['disable_succeeded', 'run_valid']
    answers['disable'] = (0, {'status': 'SUCCEEDED'}, 0.0)
    monkeypatch.setattr(h, 'setup_profile', lambda *a, **k: (Fake(), GOOD_SETUP[:2] + [('install:calendar-read', 0, 'STAGED')]))
    assert h.run_disabled_case(tmp_path, 't', 'm', 1)['failed_checks'] == ['run_valid']
    monkeypatch.setattr(h, 'setup_profile', lambda *a, **k: (Fake(), list(GOOD_SETUP)))
    answers['ask'] = (2, {'status': 'BLOCKED', 'data': {}, 'error': {'code': 'CONFIG_INVALID'}}, None)
    assert h.run_disabled_case(tmp_path, 't', 'm', 1)['pass'] is False


def test_cap05_unprobed_route_must_be_rejected_with_exit_4_before_anything_runs(monkeypatch, tmp_path):
    rejected = {'status': 'UNAVAILABLE', 'error': {'code': 'UNSUPPORTED', 'message': 'MODEL_INCOMPATIBLE'},
                'data': {'result_kind': 'BLOCKED', 'reason': 'MODEL_INCOMPATIBLE'}}
    answer = {'value': (4, rejected, 0.0)}

    class Fake:
        log = []

        def cli(self, *arguments, **options):
            return answer['value']
    steps = [('init', 0, 'SUCCEEDED'), ('install:calendar-read', 0, 'ENABLED')]
    monkeypatch.setattr(h, 'setup_profile', lambda *a, **k: (Fake(), list(steps)))
    monkeypatch.setattr(h, 'receipt_of', lambda value: None)
    failed = lambda: sorted(name for name, ok in h.run_unprobed_case(tmp_path, 't', 'm', 1)['checks'].items() if not ok)  # noqa: E731
    assert failed() == []
    answer['value'] = (5, rejected, 0.0)
    assert failed() == ['rejected_exit_4']
    answer['value'] = (4, {**rejected, 'status': 'SUCCEEDED'}, 0.0)
    assert failed() == ['not_succeeded']
    answer['value'] = (4, {'status': 'BLOCKED', 'error': {'code': 'EVIDENCE_INSUFFICIENT'}, 'data': {}}, 0.0)
    assert failed() == ['reason_model_incompatible']
    answer['value'] = (4, rejected, 0.0)
    steps[1] = ('install:calendar-read', 0, 'STAGED')
    assert failed() == ['setup_as_expected']


def test_trace_explain_binding_hash_must_be_a_digest_and_partial_is_not_available():
    unbound = _explained()
    unbound['data']['selected']['binding_hash'] = None
    assert h.trace_explain(_Profile(0, unbound), 'request-1', TARGET)['checks'][
        'explain_selected_bound_to_allow_decision'] is False
    partial = _explained()
    partial['status'] = 'PARTIAL'
    assert h.trace_explain(_Profile(0, partial), 'request-1', TARGET)['checks']['trace_explain_available'] is False


def test_failed_trace_observation_fails_the_case_without_changing_the_selection_grade():
    graded = h.apply_validity(_grade(_receipt()), *h.run_validity(GOOD_SETUP, _value()))
    failed = {'pass': False, 'checks': {'trace_explain_available': False}, 'error_code': 'UNSUPPORTED'}
    summary = h.summarize('CAP-02', [_record(graded, trace_explain=failed)], None)
    assert summary['gate_pass'] is True and summary['passed'] == 1          # selection semantics unchanged
    assert summary['observations']['trace_explain'] == {
        'requirement': 'M26-AT-01', 'n': 1, 'passed': 0, 'failed_checks': {'trace_explain_available': 1},
        'error_codes': {'UNSUPPORTED': 1}}
    assert summary['observations_pass'] is False and summary['gate_pass_with_observations'] is False
    passed = {'pass': True, 'checks': {'trace_explain_available': True}, 'error_code': None}
    assert h.summarize('CAP-02', [_record(graded, trace_explain=passed)], None)['gate_pass_with_observations'] is True


def test_evidence_writer_replaces_local_directories(tmp_path, monkeypatch):
    monkeypatch.setattr(h, 'REDACTIONS', [(str(tmp_path / 'profiles'), '<EVAL_PROFILES>')])
    h.write_evidence(tmp_path, 'x.json', {'ref': f"sha256:abc:{tmp_path / 'profiles' / 'p' / 'r.json'}"})
    assert json.loads((tmp_path / 'x.json').read_text())['ref'] == 'sha256:abc:<EVAL_PROFILES>/p/r.json'


# ------------------------------------------------------------------ the selection case run (no CLI, no provider)
class _RunProfile:
    """Stands in for a profile: answers `ask` and `trace explain` from fixed values and records the calls."""
    def __init__(self, ask, explain):
        self.answers, self.calls, self.log = {'ask': ask, 'trace': explain}, [], []

    def cli(self, *arguments, **options):
        self.calls.append(arguments)
        return self.answers[arguments[0]]


def _run_selection(monkeypatch, tmp_path, case_id, value, receipt, explain=None, ask_exit=0):
    profiles = []

    def fake_setup(base, name, *arguments, **options):
        profiles.append(_RunProfile((ask_exit, value, 0.5), (0, explain or _cap02_explained(), 0.0)))
        return profiles[-1], list(GOOD_SETUP)
    monkeypatch.setattr(h, 'setup_profile', fake_setup)
    monkeypatch.setattr(h, 'receipt_of', lambda response: receipt)
    monkeypatch.setattr(h, 'profile_cost', lambda profile: {})
    return h.run_selection_case(case_id, tmp_path, 't', 'm', 1, 7, workers=1), profiles


def _calendar_run():
    receipt = _receipt(trajectory=[
        {'tool_name': 'quati_search', 'arguments': {'query': 'appointment'}, 'candidate_ids': [CAL_READ],
         'presented_order': [CAL_READ], 'handler_executed': False},
        {'tool_name': 'quati_describe', 'arguments': {'capability_id': CAL_READ}, 'handler_executed': False},
        {'tool_name': 'quati_invoke', 'arguments': {'capability_id': CAL_READ, 'input': {'limit': 1}}, 'handler_executed': True}],
        request='Find my next appointment.')
    receipt['synthetic_evidence']['outcome'] = {'executed_capabilities': [CAL_READ + '@1.0.0']}
    receipt['synthetic_evidence']['catalog'] = [{'capability_id': CAL_READ}, {'capability_id': MAIL}]
    value = _value()
    value['data']['request_id'] = 'request-1'
    return value, receipt


def test_h5_cap02_run_asks_with_synthetic_evidence_and_reads_the_explanation_against_the_oracle(monkeypatch, tmp_path):
    value, receipt = _calendar_run()
    result, profiles = _run_selection(monkeypatch, tmp_path, 'CAP-02', value, receipt)
    assert result['n'] == 10 and result['passed'] == 10 and result['gate_pass_with_observations'] is True
    ask = next(call for call in profiles[0].calls if call[0] == 'ask')
    assert '--synthetic-evidence' in ask and '--eval-candidate-permutation-seed' in ask
    assert ('trace', 'explain', 'request-1', '--json') in profiles[0].calls
    checks = result['records'][0]['trace_explain']['checks']
    assert checks['explain_lists_the_oracle_alternatives'] and checks['explain_oracle_alternatives_have_the_oracle_reasons']
    assert checks['ask_recorded_synthetic_evidence'] is True
    # The explanation without the oracle's alternatives fails the case through its observation.
    alone = _cap02_explained()
    alone['data']['candidates'] = [_candidate(CAL_READ)]
    result, _ = _run_selection(monkeypatch, tmp_path, 'CAP-02', value, receipt, explain=alone)
    assert result['gate_pass'] is True and result['gate_pass_with_observations'] is False
    assert result['observations']['trace_explain']['failed_checks'] == {'explain_lists_the_oracle_alternatives': 10}
    # A receipt that recorded no catalog (the ask did not use `--synthetic-evidence`) fails the observation too.
    del receipt['synthetic_evidence']['catalog']
    result, _ = _run_selection(monkeypatch, tmp_path, 'CAP-02', value, receipt)
    assert result['observations']['trace_explain']['failed_checks'] == {'ask_recorded_synthetic_evidence': 10}
    assert result['gate_pass_with_observations'] is False


def test_selection_case_run_fails_on_a_golden_target_leak_a_nonzero_exit_and_a_missing_permutation(monkeypatch, tmp_path):
    def failed(result):
        return {tuple(item['failed_checks']) for item in result['failures']}
    value, receipt = _calendar_run()
    clean, profiles = _run_selection(monkeypatch, tmp_path, 'CAP-02', value, receipt)
    assert clean['failures'] == [] and clean['invalid_cases'] == 0
    assert not any(call[0] == 'trace' for call in _run_selection(monkeypatch, tmp_path, 'CAP-02', value, receipt)[1][0].calls[:1])
    leaked = _calendar_run()[1]
    leaked['synthetic_evidence']['catalog'] = [{}]
    leaked['synthetic_evidence']['model_calls'][0]['model_visible']['system'] = 'Prefer fixtures.calendar-read.'
    result, _ = _run_selection(monkeypatch, tmp_path, 'CAP-02', value, leaked)
    assert result['passed'] == 0 and failed(result) == {('no_golden_target_leak',)} and result['invalid_cases'] == 10
    result, _ = _run_selection(monkeypatch, tmp_path, 'CAP-02', value, receipt, ask_exit=4)
    assert result['passed'] == 0 and failed(result) == {('exit_code_0',)}
    unshuffled = _calendar_run()[1]
    del unshuffled['synthetic_evidence']['trajectory'][0]['presented_order']
    result, _ = _run_selection(monkeypatch, tmp_path, 'CAP-02', value, unshuffled)
    assert result['passed'] == 0 and failed(result) == {('permutation_recorded',)}
