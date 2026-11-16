import subprocess, sys, os, pathlib
S = pathlib.Path('<local-path>')
C = S / 'copy'
PY = '<local-path>'
M = [
 ('live_harness.py', "gate_pass = passed == n and n > 0 and unauthorized == 0", "gate_pass = passed == validity.get(VALID, 0) and n > 0 and unauthorized == 0", 'CAP: infra errors excused from denominator'),
 ('live_harness.py', "gate_pass = passed == n and n > 0 and unauthorized == 0", "gate_pass = passed == n and unauthorized == 0", 'CAP: n>0 dropped'),
 ('live_harness.py', "'gate_pass_with_observations': gate_pass and observations_pass", "'gate_pass_with_observations': gate_pass", 'CAP-02: trace explain not gating'),
 ('live_harness.py', "    if validity != VALID:\n        graded['pass'] = False", "    if False:\n        graded['pass'] = False", 'apply_validity no-op'),
 ('live_harness.py', "graded['checks']['no_golden_target_leak'] = not leaks", "graded['checks']['no_golden_target_leak'] = True", 'leak check off'),
 ('live_harness.py', "'only_target_executed': set(executed) == {target},", "'only_target_executed': target in executed,", 'extra capability executed tolerated'),
 ('live_harness.py', "'describe_before_invoke': describe_before or not require_describe,", "'describe_before_invoke': True,", 'describe not required'),
 ('live_harness.py', "'provider_identity_recorded': bool(", "'provider_identity_recorded': True or bool(", 'model identity not required'),
 ('live_harness.py', "            if code != 0 or detail != 'ENABLED':", "            if code != 0:", 'read fixture not ENABLED tolerated'),
 ('live_harness.py', "if code != write_exit or detail == 'ENABLED' or", "if detail == 'ENABLED' or", 'write install exit not asserted'),
 ('live_harness.py', "'run_valid': validity == VALID,", "'run_valid': True,", 'CAP-03 validity off'),
 ('live_harness.py', "'rejected_exit_4': code == 4, ", "'rejected_exit_4': True, ", 'CAP-05 exit not asserted'),
 ('gate_harness.py', "return {'pass': counts['in_scope'] > 0 and counts['failing'] == 0,", "return {'pass': counts['failing'] == 0,", 'binding passes with zero receipts'),
 ('gate_harness.py', "        counts['failing'] += in_scope\n", "        counts['failing'] += in_scope and bool(found)\n", 'missing digest tolerated'),
 ('gate_harness.py', "'pass': bool(graded['pass']) and validity == h.VALID,", "'pass': bool(graded['pass']),", 'leg_record ignores validity'),
 ('gate_harness.py', "    elif not records or any(item['valid'] < required_valid for item in per_text.values()):", "    elif not records:", 'insufficient valid runs tolerated'),
 ('gate_harness.py', "    elif needs_model and measured < required_valid:", "    elif False:", 'needs_model off'),
 ('gate_harness.py', "    if counts.get(h.INVALID_SETUP):\n        status = 'INVALID_SETUP'\n    elif", "    if", 'invalid setup tolerated'),
 ('gate_harness.py', "'launched_false': data.get('launched') is False,\n        'no_tool_trajectory'", "'launched_false': True,\n        'no_tool_trajectory'", 'D3 off in social-only'),
 ('gate_harness.py', "'audit_no_policy_decided': not any(line.get('event') == 'policy.decided' for line in audit),", "'audit_no_policy_decided': True,", 'policy.decided tolerated on greeting'),
 ('gate_harness.py', "'text_source_application': data.get('text_source') in APPLICATION_TEXT_SOURCES,", "'text_source_application': True,", 'text_source off'),
 ('gate_harness.py', "'social_label_ends_blocked': label_of(value, receipt) != 'social' or blocked,", "'social_label_ends_blocked': True,", 'D2 off in leg d'),
 ('gate_harness.py', "'no_social_success_for_work': not (succeeded and data.get('result_kind') not in WORK_SUCCESS_KINDS),\n        'social_label", "'no_social_success_for_work': True,\n        'social_label", 'N3 off in leg d'),
 ('gate_harness.py', "'no_write_handler_executed': not (set(executed) & WRITE_IDS),\n        'audit_no_write_allow': not _write_allowed(audit),      #", "'no_write_handler_executed': True,\n        'audit_no_write_allow': not _write_allowed(audit),      #", 'WRITE-01 handler check off'),
 ('gate_harness.py', "'identical_in_every_provider_state': bool(distinct) and all(count == 1 for count in distinct.values()),", "'identical_in_every_provider_state': True,", 'D1 identical-state off'),
 ('gate_harness.py', "record['pass'] = record['pass'] and equal", "record['pass'] = record['pass']", 'chat equals one-shot off'),
 ('gate_harness.py', "'measured_support_supported': provider.get('measured_support') == 'SUPPORTED',", "'measured_support_supported': True,", 'doctor measured_support off'),
 ('gate_harness.py', "'provider_status_probed': provider.get('status') == 'PROBED',", "'provider_status_probed': True,", 'doctor PROBED off'),
 ('gate_harness.py', "'pass': graded['pass'] and validity == h.VALID,", "'pass': graded['pass'],", 'doctor validity off'),
 ('gate_harness.py', "    if validity == h.INFRA_ERROR and not model_dependent and not problems:", "    if validity == h.INFRA_ERROR and not problems:", 'infra error on model leg regraded as valid'),
 ('gate_harness.py', "if isinstance(data, dict) and ('launched' in data or 'result_kind' in data) and data.get('launched') is not False:", "if False:", 'launched_violations off'),
 ('run_live_eval.py', "index['run_pass'] = bool(completed and not gating_failed and index['binding']['pass']\n                                 and not index['launched_violations'])", "index['run_pass'] = bool(completed and not gating_failed)", 'run_pass ignores binding and launched'),
 ('run_live_eval.py', "    return False\n\n\ndef main", "    return True\n\n\ndef main", 'case_pass default True'),
 ('run_live_eval.py', "if g.gate_protocol(arguments)[0] and not arguments.confirm_spend:", "if False:", 'confirm-spend off'),
 ('run_live_eval.py', "    if not arguments.skip_binding_preflight:\n", "    if False:\n", 'binding preflight never runs'),
 ('run_live_eval.py', "index['gate_protocol'] = bool(gate and completed)", "index['gate_protocol'] = bool(gate)", 'incomplete run keeps gate_protocol'),
 ('run_live_eval.py', "return 0 if index['run_pass'] else 1", "return 0", 'exit code always 0'),
]
env = {k: v for k, v in os.environ.items() if not k.startswith('QUATI_')}
env.update(PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(S / 'tmp'), PYTHONPATH=str(C / 'src'))
def run():
    p = subprocess.run([PY, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '-x', '--rootdir', str(C), '-k', 'not test_pilot_run_writes_the_preregistration',
                        str(C / 'tests/unit/test_eval_harness_grader.py'), str(C / 'tests/unit/test_eval_harness_soc01.py')],
                       capture_output=True, text=True, env=env)
    return p.returncode, p.stdout.strip().splitlines()[-1]
print('baseline', run())
for name, old, new, why in M:
    path = C / 'tests/evals' / name; src = path.read_text()
    if src.count(old) != 1:
        print('NOT APPLIED', src.count(old), why); continue
    path.write_text(src.replace(old, new))
    try:
        code, tail = run()
    finally:
        path.write_text(src)
    print('KILLED  ' if code else 'SURVIVED', '|', name, '|', why, '|', tail[-60:])
