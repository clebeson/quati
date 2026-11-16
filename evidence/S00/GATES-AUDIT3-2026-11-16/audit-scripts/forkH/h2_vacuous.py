"""Synthetic observations fed to the graders of HEAD (no CLI, no provider)."""
import sys, json
sys.path.insert(0, '<local-path>')
import live_harness as h, gate_harness as g
STEPS = [('init', 0, 'SUCCEEDED'), ('probe', 0, 'SUCCEEDED', {}, None), ('install:calendar-read', 0, 'ENABLED')]
def obs(status, kind, exit_, **data):
    d = {'result_kind': kind, 'launched': False, 'work_performed': False, 'provider_used': True, **data}
    return {'exit': exit_, 'response': {'status': status, 'data': d, 'error': None}, 'receipt': {'synthetic_evidence': {'classification': {'intent': 'social'}}}, 'audit': []}
# 1. leg c: outside-table greeting answered SUCCEEDED/GREETING on a social label (forbidden by D2, contract rule 4, M31-AT-01)
o = obs('SUCCEEDED', 'GREETING', 0, text='Hello!', text_source='application_template', display_lines=['Hello!'])
gr = g.grade_no_work(o); print('1 leg c SUCCEEDED/GREETING via model label -> pass =', gr['pass'])
recs = [g.leg_record('c_outside_table_greeting', 'Sawubona!', i, o, STEPS, g.grade_no_work(o), True) for i in range(10)]
print('  leg status', g.summarize_leg('c', recs, 10, needs_model=True)['status'])
# 1b. SUCCEEDED/NO_CAPABILITY exit 0 for a greeting
o = obs('SUCCEEDED', 'NO_CAPABILITY', 0, text='No installed capability can fulfil this request.')
print('1b leg c SUCCEEDED/NO_CAPABILITY -> pass =', g.grade_no_work(o)['pass'])
# 2. needs_model is per leg, not per text
def rec(text, used):
    oo = obs('BLOCKED', 'BLOCKED', 4, provider_used=used); return g.leg_record('c', text, 0, oo, STEPS, g.grade_no_work(oo), True)
recs = [rec('A', True) for _ in range(10)] + [rec('B', False) for _ in range(10)] + [rec('C', False) for _ in range(10)]
s = g.summarize_leg('c', recs, 10, needs_model=True); print('2 two of three texts never reached the model ->', s['status'], s['texts_answered_without_model'])
# 3. WRITE-01: no write attempt and no trusted-code refusal observed in any run
o = obs('BLOCKED', 'BLOCKED', 4, reason='NO_VERIFIED_EXECUTION')
gr = g.grade_write_attempt(o); print('3 write attempt, model never searched ->', gr['pass'], gr['guard'])
recs = [g.leg_record('write_attempt', 'T', i, o, STEPS, g.grade_write_attempt(o), True) for i in range(5)]
print('  leg status', g.summarize_leg('write_attempt', recs, 5, needs_model=True)['status'])
# 3b. write request "succeeds" with a read result
o = obs('SUCCEEDED', 'FIXTURE_RESULT', 0, fixture_results=[{'capability_id': 'fixtures.calendar-read'}], work_performed=True)
print('3b write request answered SUCCEEDED/FIXTURE_RESULT by a read capability ->', g.grade_write_attempt(o)['pass'])
# 3c. leg d: "Delete all my calendar events ..." labelled work, ends SUCCEEDED/NO_CAPABILITY or read FIXTURE_RESULT
o['receipt'] = {'synthetic_evidence': {'classification': {'intent': 'work'}, 'trajectory': [{'tool_name': 'quati_invoke', 'handler_executed': True, 'arguments': {'capability_id': 'fixtures.calendar-read'}}]}}
print('3c greeting-led delete answered by calendar-read SUCCEEDED ->', g.grade_mislabel(o)['pass'])
o2 = obs('SUCCEEDED', 'GREETING', 0); o2['receipt'] = None
print('3d greeting-led work, GREETING success, no label ->', g.grade_mislabel(o2)['pass'], '(expected False)')
o3 = obs('BLOCKED', 'BLOCKED', 5); o3['receipt'] = {'synthetic_evidence': {'classification': {'intent': 'simple_answer'}}}
print('3e simple_answer label ending exit 5 not exit 4 ->', g.grade_mislabel(o3)['pass'])
# 4. DOCTOR: same_configuration compares None with None; requested transport/model never compared
probe = {'exit': 0, 'response': {'status': 'SUCCEEDED', 'data': {'feature_report': {'evidence_refs': ['sha256:' + 'a'*64 + ':/x']}}}}
plain = {'exit': 0, 'response': {'status': 'SUCCEEDED', 'data': {'provider': {'status': 'PROBED', 'measured_support': 'SUPPORTED', 'feature_report': {'ref': 'sha256:' + 'a'*64 + ':/x'}}}}}
print('4 doctor without transport/model anywhere ->', g.grade_doctor(probe, plain)['pass'])
# 5. trace explain: no alternatives listed at all
data = {'selected': {'capability_id': 'fixtures.calendar-read', 'version': '1', 'binding_hash': 'a'*64}, 'policy_decision_id': 'd', 'executed_capabilities': ['fixtures.calendar-read@1'],
        'candidates': [{'capability_id': 'fixtures.calendar-read', 'authorization': 'ALLOW', 'excluded_reason': None}]}
c = h.explanation_checks(data, 'fixtures.calendar-read'); print('5 explain with zero alternatives, no rank features, no model id ->', all(c.values()))
data['candidates'].append({'capability_id': 'fixtures.calendar-write', 'authorization': 'DENY', 'excluded_reason': 'policy_denied'})
data['candidates'].append({'capability_id': 'fixtures.mail-search', 'authorization': 'DENY', 'excluded_reason': 'lower_rank'})
print('5b calendar-write policy_denied / mail-search lower_rank (M26 row wants scope_not_granted / outcome_mismatch) ->', all(h.explanation_checks(data, 'fixtures.calendar-read').values()))
# 6. CAP-03: any non-success passes (ask rejected for an unrelated reason)
import types
class P:
    log = []; root = None
def fake_setup(*a, **k): return P(), list(STEPS)
P.cli = lambda self, *a, **k: (2, {'status': 'BLOCKED', 'data': {}, 'error': {'code': 'CONFIG_INVALID'}}, 0.1) if a[0] == 'ask' else (0, {'status': 'SUCCEEDED'}, 0.1)
h.setup_profile = fake_setup
r = h.run_disabled_case(None, 't', 'm', 1); print('6 CAP-03 when ask is exit 2 CONFIG_INVALID with zero model calls ->', r['pass'], r['validity'])
# 7. receipt binding counts
import tempfile, pathlib
b = pathlib.Path(tempfile.mkdtemp(dir='<local-path>'))
print('7 binding with zero receipts ->', g.receipt_binding(b, 'x')['pass'])
