"""Deterministic tests of the live-evaluation oracle (tests/evals/live_harness.py).

Risk boundary: S00-GATE-02 grading must not be lenient (TEST_CASES CAP-01/CAP-02, M15-RT-01).
These run on synthetic receipts only; they spend nothing and prove nothing about a provider.
"""
import copy
import sys
from pathlib import Path

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
