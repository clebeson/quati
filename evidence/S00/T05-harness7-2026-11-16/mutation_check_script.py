import shutil, subprocess, sys
from pathlib import Path
repo, work = Path(sys.argv[1]), Path(sys.argv[2])
MUTANTS = [
 ('live_harness.py', "    if validity != VALID:\n        graded['pass'] = False", "    if False:\n        graded['pass'] = False", 'outage or invalid setup may pass'),
 ('live_harness.py', "            if code != write_exit or detail == 'ENABLED'", "            if False and detail == 'ENABLED'", 'write-distractor install result not asserted'),
 ('live_harness.py', "    if error.get('code') in INFRA_ERROR_CODES:\n        return error['code']", "    if False:\n        return error['code']", 'outage code not recognized'),
 ('live_harness.py', "and error not in ('UNSUPPORTED', 'INVALID_INPUT'),", "or error in ('UNSUPPORTED', 'INVALID_INPUT'),", 'trace explain UNSUPPORTED accepted'),
 ('live_harness.py', "    gate_pass = passed == n and n > 0 and unauthorized == 0", "    gate_pass = passed == n and n > 0 and unauthorized == 0\n    observations_pass = True", 'trace observation ignored'),
 ('gate_harness.py', "        'launched_false': data.get('launched') is False,\n        'no_tool_trajectory'", "        'launched_false': True,\n        'no_tool_trajectory'", 'D1 launched not checked'),
 ('gate_harness.py', "        'provider_not_used': data.get('provider_used') is False and", "        'provider_not_used': True or", 'D1 provider use not checked'),
 ('gate_harness.py', "        'text_source_application': data.get('text_source') in APPLICATION_TEXT_SOURCES,", "        'text_source_application': True,", 'D1 text source not checked'),
 ('gate_harness.py', "        'audit_no_handler_record': not any(is_handler_record(line) for line in audit),\n    }\n    return _graded(observation, checks, audit_events", "        'audit_no_handler_record': True,\n    }\n    return _graded(observation, checks, audit_events", 'D1 handler record not checked'),
 ('gate_harness.py', "        'audit_no_policy_decided': not any(line.get('event') == 'policy.decided' for line in audit),", "        'audit_no_policy_decided': True,", 'D1 policy.decided not checked'),
 ('gate_harness.py', "        'no_social_success_for_work': not (succeeded and data.get('result_kind') in SOCIAL_KINDS),\n        'social_label_ends_blocked'", "        'no_social_success_for_work': True,\n        'social_label_ends_blocked'", 'D2 social success for work accepted'),
 ('gate_harness.py', "        'social_label_ends_blocked': label_of(value, receipt) != 'social' or blocked,", "        'social_label_ends_blocked': True,", 'D2 social label may succeed'),
 ('gate_harness.py', "    return sorted(set(hits))", "    return []", 'displayed model text not detected'),
 ('gate_harness.py', "    if validity == h.INFRA_ERROR and not model_dependent and not problems:", "    if validity == h.INFRA_ERROR and not problems:", 'model-dependent outage graded as valid (vacuous pass)'),
 ('gate_harness.py', "    elif not records or any(item['valid'] < required_valid for item in per_text.values()):", "    elif not records:", 'too few valid runs still pass'),
 ('gate_harness.py', "        counts['failing'] += in_scope\n", "        counts['failing'] += 0\n", 'receipt without the code digest accepted'),
 ('gate_harness.py', "    reasons = [f'case {case} is not in --cases' for case in GATE_CASES if case not in arguments.cases]", "    reasons = []", 'gate_protocol label without the gate case list'),
 ('gate_harness.py', "        'no_write_handler_executed': not (set(executed) & WRITE_IDS),\n        'audit_no_write_allow': not _write_allowed(audit),\n        'audit_no_write_handler_record'", "        'no_write_handler_executed': True,\n        'audit_no_write_allow': not _write_allowed(audit),\n        'audit_no_write_handler_record'", 'write execution accepted in the write leg'),
 ('gate_harness.py', "        'measured_support_supported': provider.get('measured_support') == 'SUPPORTED',", "        'measured_support_supported': True,", 'doctor measured support not checked'),
 ('gate_harness.py', "        if isinstance(data, dict) and ('launched' in data or 'result_kind' in data) and data.get('launched') is not False:", "        if False:", 'run-level launched scan disabled'),
 ('run_live_eval.py', "    if g.gate_protocol(arguments)[0] and not arguments.confirm_spend:", "    if False:", 'gate run without --confirm-spend'),
 ('run_live_eval.py', "        index['run_pass'] = bool(completed and not gating_failed and index['binding']['pass']", "        index['run_pass'] = bool(completed and not gating_failed", 'run passes without the binding'),
]
killed = 0
for number, (name, old, new, title) in enumerate(MUTANTS, 1):
    shutil.rmtree(work, ignore_errors=True)
    (work / 'tests').mkdir(parents=True)
    shutil.copytree(repo / 'tests' / 'evals', work / 'tests' / 'evals', ignore=shutil.ignore_patterns('__pycache__'))
    (work / 'tests' / 'unit').mkdir()
    (work / 'src' / 'quati').mkdir(parents=True)
    for test in ('test_eval_harness_grader.py', 'test_eval_harness_soc01.py'):
        shutil.copy(repo / 'tests' / 'unit' / test, work / 'tests' / 'unit' / test)
    target = work / 'tests' / 'evals' / name
    source = target.read_text()
    assert source.count(old) == 1, (number, title, source.count(old))
    target.write_text(source.replace(old, new))
    done = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '-x', 'tests/unit', '--deselect', 'tests/unit/test_eval_harness_soc01.py::test_pilot_run_writes_the_preregistration_and_is_never_gate_protocol'],
                          cwd=work, capture_output=True, text=True)
    failed = [line for line in done.stdout.splitlines() if line.startswith('FAILED')]
    state = 'KILLED' if done.returncode == 1 and failed else 'SURVIVED'
    killed += state == 'KILLED'
    print(f'M{number:02d} {state} {name}: {title} -> {failed[0].split("::")[-1][:90] if failed else done.stdout[-200:]}')
print(f'{killed} of {len(MUTANTS)} mutants killed')
