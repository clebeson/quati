"""Run the S00 blind live evaluation and write evidence/S00/T05-<run-id>/.

Spends real money on the operator's own provider sign-in. Gate requalification (one run produces the
evidence for the live part of S00-GATE-01, for S00-GATE-02 and for S00-GATE-03):

    .venv/bin/python tests/evals/run_live_eval.py --transport claude_cli --model haiku \
        --heldout --workers 4 --label gate7 --confirm-spend

The default case list is the gate list (DOCTOR, CAP-01, CAP-02, CAP-03, CAP-05, SOC-01, WRITE-01) plus
the informational behavior suite. The gate protocol is `--runs 3` (10 paraphrases x 3), `--soc-runs`
of at least 10 per text and `--write-runs` of at least 5 per text, against the real CLI. Any other
combination is a pilot: its INDEX says NOT_GATE_EVIDENCE and `gate_protocol` is false.

The estimated number of provider calls is printed first (`--estimate-only` stops there). A gate-protocol
run needs `--confirm-spend`. PREREG.json is written before the first provider call. After the last case
the run fails unless every receipt of every profile carries the pre-registered code digest and every
ask Response reports `launched` false. The exit code is 0 only when the run passed.

This harness never seals a gate: its verdict is input for the independent audit.
"""
import argparse
import json
import shlex
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import live_harness as h  # noqa: E402
import gate_harness as g  # noqa: E402

DRY_RUN_LAUNCHER = Path(__file__).resolve().parent / 'dryrun_scripted_cli.py'
GATES = {'S00-GATE-01 (live doctor observation)': ('DOCTOR',), 'S00-GATE-02': ('CAP-01', 'CAP-02'),
         'S00-GATE-03': ('SOC-01', 'WRITE-01')}
BRIEF_KEYS = ('case_id', 'n', 'valid_n', 'passed', 'gate_pass', 'gate_pass_with_observations', 'status',
              'wilson95_lower', 'unauthorized_effects', 'infra_errors', 'invalid_setup', 'observed_models',
              'cost_usd_total_known', 'cost_usd_all_receipts', 'elapsed_s_p50', 'elapsed_s_max',
              'distinct_digest_values', 'checks', 'failed_checks', 'validity', 'leg_status', 'not_run_legs',
              'outcome_distribution', 'distinct_answers_per_social_text', 'guard_distribution',
              'policy_gate_answered_runs', 'succeeded_with_read_only_result_runs', 'write_handler_executions',
              'feature_report_sha256', 'observations')


def parse(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--transport', default='claude_cli')
    parser.add_argument('--model', default='haiku')
    parser.add_argument('--cases', nargs='+', default=[*g.GATE_CASES, 'BEH'],
                        choices=[*g.GATE_CASES, 'BEH'], metavar='CASE')
    parser.add_argument('--runs', type=int, default=g.GATE_RUNS, help='runs per CAP-01/CAP-02 paraphrase')
    parser.add_argument('--soc-runs', type=int, default=g.GATE_SOC_RUNS, help='runs per SOC-01 text')
    parser.add_argument('--write-runs', type=int, default=g.GATE_WRITE_RUNS, help='runs per write-attempt text')
    parser.add_argument('--heldout', action='store_true',
                        help='also run the held-out CAP-01/CAP-02 paraphrases (reported, never gating)')
    parser.add_argument('--heldout-runs', type=int, default=g.GATE_RUNS)
    parser.add_argument('--workers', type=int, default=4, help='profiles evaluated in parallel')
    parser.add_argument('--seed', type=int, default=20261116)
    parser.add_argument('--judge-model', default='sonnet')
    parser.add_argument('--label', default='')
    parser.add_argument('--out', default=None, help='evidence directory (default evidence/S00/T05-<run-id>)')
    parser.add_argument('--keep-profiles', action='store_true')
    parser.add_argument('--confirm-spend', action='store_true', help='required for a gate-protocol run')
    parser.add_argument('--estimate-only', action='store_true', help='print the estimate and stop')
    parser.add_argument('--binding-scope', choices=('all', 'request'), default='all',
                        help="receipts that must carry the pre-registered code digest: every receipt, or only "
                             "the receipts of requests (the others are then reported, not required)")
    parser.add_argument('--skip-binding-preflight', action='store_true')
    parser.add_argument('--timeout-fault-env', action='append', default=[], metavar='NAME=VALUE',
                        help='public product configuration that makes classification time out (SOC-01 leg f); '
                             'without it the leg is recorded NOT_RUN')
    parser.add_argument('--staged-write-install-args', default='',
                        help='extra `capabilities install-fixture` arguments for the write fixtures of WRITE-01 '
                             '(operator-staged option, decision D5); off by default')
    parser.add_argument('--staged-write-expect-exit', type=int, default=0)
    parser.add_argument('--staged-write-expect-lifecycle', default='STAGED')
    parser.add_argument('--vendor-cli', choices=('auto', 'none'), default='auto',
                        help='record `<vendor> --version` in the pre-registration (no model call)')
    parser.add_argument('--dry-run-scripted', action='store_true',
                        help='plumbing check with the scripted, network-free model of the unit tests; '
                             'never evidence of a provider and never gate protocol')
    return parser.parse_args(argv)


def run_case(case, arguments, base):
    transport, model, seed, workers = arguments.transport, arguments.model, arguments.seed, arguments.workers
    if case == 'DOCTOR':
        return g.run_doctor_leg(base, transport, model)
    if case in ('CAP-01', 'CAP-02'):
        return h.run_selection_case(case, base, transport, model, arguments.runs, seed, workers)
    if case in ('CAP-01-HELDOUT', 'CAP-02-HELDOUT'):
        sealed = case.removesuffix('-HELDOUT')
        return h.run_selection_case(sealed, base, transport, model, arguments.heldout_runs, seed, workers,
                                    dataset=f'{sealed.lower().replace("-", "")}_heldout.json', report_id=case)
    if case == 'CAP-03':
        return h.run_disabled_case(base, transport, model, seed)
    if case == 'CAP-05':
        return h.run_unprobed_case(base, transport, model, seed)
    if case == 'SOC-01':
        fault = dict(item.split('=', 1) for item in arguments.timeout_fault_env)
        return g.run_soc01_gate(base, transport, model, seed, workers, arguments.soc_runs, fault or None)
    if case == 'WRITE-01':
        staged = tuple(shlex.split(arguments.staged_write_install_args))
        if staged:
            return g.run_write_attempts(base, transport, model, seed, workers, arguments.write_runs, staged,
                                        arguments.staged_write_expect_exit, {arguments.staged_write_expect_lifecycle})
        return g.run_write_attempts(base, transport, model, seed, workers, arguments.write_runs)
    if case == 'BEH':
        return h.run_behavior_suite(base, transport, model, arguments.judge_model, seed, workers)
    raise SystemExit(f'unknown case {case}')


def case_pass(result) -> bool:
    for key in ('gate_pass_with_observations', 'gate_pass', 'pass'):
        if key in result:
            return bool(result[key])
    return False


def main(argv=None):
    arguments = parse(argv)
    if any('=' not in item for item in arguments.timeout_fault_env):
        raise SystemExit('--timeout-fault-env takes NAME=VALUE')
    if arguments.dry_run_scripted:
        h.LAUNCHER, h.ALLOW_LIVE = (sys.executable, str(DRY_RUN_LAUNCHER)), False  # the venv interpreter
        arguments.judge_model = ''  # the judge is a real model: a dry run never calls it
    launcher_replaced = h.LAUNCHER is not None
    cases = list(arguments.cases) + (['CAP-01-HELDOUT', 'CAP-02-HELDOUT'] if arguments.heldout else [])
    estimate = g.estimate_calls(arguments)
    print('ESTIMATE ' + json.dumps(estimate, sort_keys=True), flush=True)
    print(f"ESTIMATE provider calls: about {estimate['typical_calls']} (ceiling {estimate['max_calls']}); "
          f"about US${estimate['usd_typical_at_haiku_rate']} at the haiku rate of the gate6 run", flush=True)
    if arguments.estimate_only:
        return 0
    # The spend confirmation depends on what was asked for, not on which launcher answers.
    if g.gate_protocol(arguments)[0] and not arguments.confirm_spend:
        print('STOPPED: a gate-protocol run needs --confirm-spend (nothing was run, no evidence was written).')
        return 2
    expected_digest = h.code_digest(h.SOURCE / 'quati')
    if not arguments.skip_binding_preflight:
        preflight = g.binding_preflight(arguments.transport, arguments.model, expected_digest, arguments.binding_scope)
        if not preflight['pass']:
            print('BINDING_PREFLIGHT_FAILED ' + json.dumps(
                {key: preflight[key] for key in ('scope', 'receipts', 'missing', 'mismatched', 'unreadable',
                                                 'missing_by_kind', 'steps')}, sort_keys=True))
            print('STOPPED before any provider call: a receipt written without a provider does not carry the '
                  'pre-registered code digest, so the run could not pass its binding check.')
            return 2

    run_id = f'{h.now_id()}-{arguments.transport}-{arguments.model}{("-" + arguments.label) if arguments.label else ""}'
    out = Path(arguments.out) if arguments.out else h.ROOT / 'evidence' / 'S00' / f'T05-{run_id}'
    out.mkdir(parents=True)
    base = Path(tempfile.mkdtemp(prefix='quati-eval-'))
    h.REDACTIONS[:] = [(str(base), '<EVAL_PROFILES>'), (str(h.ROOT), '<REPO>'), (str(Path.home()), '<HOME>')]
    vendor = ({'version': 'NOT_RECORDED', 'reason': 'launcher replaced or --vendor-cli none'}
              if launcher_replaced or arguments.vendor_cli == 'none' else g.vendor_cli_version(arguments.transport))
    # Pre-registration (TEST_EXECUTION_PROTOCOL): everything that fixes the run is hashed and written
    # before the first provider call, so scoring cannot silently change after results are seen.
    prereg = g.preregistration(arguments, run_id, cases, Path(__file__), vendor, launcher_replaced)
    gate, gate_reasons = prereg['gate_protocol_requested'], prereg['gate_protocol_reasons']
    index = {'run_id': run_id, 'transport': arguments.transport, 'model': arguments.model,
             'runs_per_utterance': arguments.runs, 'soc_runs': arguments.soc_runs, 'write_runs': arguments.write_runs,
             'seed': arguments.seed, 'judge_model': arguments.judge_model, 'cases': cases,
             'gate_protocol_requested': gate, 'gate_protocol_reasons': gate_reasons,
             'launcher_replaced': launcher_replaced, 'harness_sha256': prereg['harness_sha256'], 'files': {},
             'summary': {}, 'launched_violations': [], 'cases_completed': []}
    index['preregistration_sha256'] = h.write_evidence(out, 'PREREG.json', prereg)
    try:
        for case in cases:
            result = run_case(case, arguments, base)
            index['files'][case] = h.write_evidence(out, f'{case}.json', result)
            brief = {key: result[key] for key in BRIEF_KEYS if key in result}
            brief.update({'pass': case_pass(result), 'gating': case in g.GATE_CASES})
            if result.get('failures'):
                brief['failures'] = result['failures']
            if result.get('per_case'):
                brief['per_case'] = {k: {x: v[x] for x in ('pass', 'validity', 'status', 'executed', 'judge')} | {
                    'failed': sorted(c for c, ok in v['checks'].items() if not ok)} for k, v in result['per_case'].items()}
            index['summary'][case] = brief
            index['launched_violations'] += [{'case': case, **item} for item in g.launched_violations(result)]
            index['cases_completed'].append(case)
            print(json.dumps(brief, sort_keys=True, default=str), flush=True)
    finally:
        summary = index['summary']
        index['binding'] = g.receipt_binding(base, expected_digest, arguments.binding_scope)
        completed = all(case in summary for case in cases)
        # gate_protocol is true only when the full gate case list ran, to the end, with the gate repetitions.
        index['gate_protocol'] = bool(gate and completed)
        gating_failed = sorted(case for case in cases if case in g.GATE_CASES and not summary.get(case, {}).get('pass'))
        index['gating_cases_failed'] = gating_failed
        index['run_pass'] = bool(completed and not gating_failed and index['binding']['pass']
                                 and not index['launched_violations'])
        index['gates'] = {name: ('NOT_RUN' if not all(case in summary for case in needed) else
                                 'PASS' if all(summary[case]['pass'] for case in needed) else 'FAIL')
                          for name, needed in GATES.items()}
        not_run = (summary.get('SOC-01') or {}).get('not_run_legs') or {}
        if not index['gate_protocol']:
            index['verdict'] = 'NOT_GATE_EVIDENCE: ' + ('; '.join(gate_reasons) or 'the run did not complete')
        elif not index['run_pass']:
            index['verdict'] = 'GATE_PROTOCOL_FAIL'
        else:
            index['verdict'] = 'GATE_PROTOCOL_PASS_WITH_NOT_RUN_LEGS' if not_run else 'GATE_PROTOCOL_PASS'
        index['index_note'] = ('Gate protocol: 10 paraphrases x 3 runs per selection case, SOC-01 legs with at least '
                               '10 runs per text, write attempts with at least 5 runs per text. The verdict is input '
                               'for the independent audit and never a seal.' if index['gate_protocol'] else
                               'Pilot or partial run (not gate evidence).')
        h.write_evidence(out, 'INDEX.json', index)
        if not arguments.keep_profiles:
            shutil.rmtree(base, ignore_errors=True)
    print(json.dumps({key: index[key] for key in ('verdict', 'run_pass', 'gates', 'gating_cases_failed')}
                     | {'binding': {key: index['binding'][key] for key in ('pass', 'scope', 'receipts', 'missing',
                                                                           'mismatched', 'missing_by_kind')},
                        'launched_violations': len(index['launched_violations'])}, sort_keys=True))
    print(f'EVIDENCE {out}')
    return 0 if index['run_pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
