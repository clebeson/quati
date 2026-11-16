"""Run the S00 blind live evaluation and write evidence/S00/T05-<run-id>/.

Spends real money on the operator's own provider sign-in. Gate requalification (one run produces the
evidence for the live part of S00-GATE-01, for S00-GATE-02 and for S00-GATE-03):

    .venv/bin/python tests/evals/run_live_eval.py --transport claude_cli --model haiku \
        --workers 4 --label gate8 --accept-not-run f_classification_timeout --confirm-spend

The default case list is the gate list (DOCTOR, CAP-01, CAP-02, CAP-03, CAP-05, SOC-01, WRITE-01) plus
the informational behavior suite. The gate protocol is `--runs 3` (10 paraphrases x 3), `--soc-runs`
of at least 10 per text and `--write-runs` of at least 5 per text, against the real CLI. Any other
combination is a pilot: its INDEX says NOT_GATE_EVIDENCE and `gate_protocol` is false. `--heldout` adds the
held-out CAP-01 / CAP-02 paraphrases, which are informational and never gating.

Order of a run, everything before the first case being free of provider calls:

1. The plan and the estimated provider calls and cost (typical and ceiling) are printed. `--estimate-only`
   stops here.
2. Any run that can make a provider call needs `--confirm-spend`, a pilot included. Only `--estimate-only`
   and `--dry-run-scripted` (network-free scripted model) are exempt.
3. The pre-registration is built: code digest, harness, datasets, asset files (contracts, behavior
   packages, statecharts, policy template), the product's own `doctor` identity, git state, gate sentences.
   A gate-protocol run is REFUSED when the working tree is dirty (changed tracked files, or untracked files
   not named with `--allow-untracked PATH`), when `src/quati/assets` shadows the repository assets, when
   the doctor identity or a gate sentence cannot be read, or when the SOC-01 texts do not match the
   product's social table (checked with no provider configured).
4. PREREG.json is written, then the cases run.
5. After the last case the run fails unless every receipt of every profile carries the pre-registered code
   digest (and the product's own asset digest, when `doctor` reports one), every doctor Response reports the
   pre-registered behavior section and every ask Response reports `launched` false.

A gate whose cases passed while a required leg was NOT_RUN is printed as PASS_WITH_NOT_RUN_LEGS, never as
PASS, with the legs and the reason. The exit code is 0 only when the run passed and every NOT_RUN leg was
named with `--accept-not-run LEG`; 1 when the run failed; 2 when it was stopped before any call; 3 when it
passed but a NOT_RUN leg was not accepted.

This harness never seals a gate: its verdict is input for the independent audit.
"""
import argparse
import json
import os
import shlex
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import live_harness as h  # noqa: E402
import gate_harness as g  # noqa: E402

DRY_RUN_LAUNCHER = Path(__file__).resolve().parent / 'dryrun_scripted_cli.py'
# The route the dry-run launcher always answers with (tests/unit/s00_t04_support.py: FAKE_TRANSPORT and the
# model id of its scripted provider). A dry run is run and graded for this route, whatever --transport says.
DRY_RUN_ROUTE = ('scripted_fake_t04', 'fake-model-1')
GATES = {'S00-GATE-01 (live doctor observation)': ('DOCTOR',), 'S00-GATE-02': ('CAP-01', 'CAP-02'),
         'S00-GATE-03': ('SOC-01', 'WRITE-01')}
BRIEF_KEYS = ('case_id', 'n', 'valid_n', 'passed', 'gate_pass', 'gate_pass_with_observations', 'status',
              'wilson95_lower', 'unauthorized_effects', 'infra_errors', 'invalid_setup', 'observed_models',
              'cost_usd_total_known', 'cost_usd_all_receipts', 'elapsed_s_p50', 'elapsed_s_max',
              'distinct_digest_values', 'checks', 'failed_checks', 'validity', 'leg_status', 'not_run_legs',
              'outcome_distribution', 'distinct_answers_per_social_text', 'guard_distribution',
              'policy_gate_answered_runs', 'succeeded_with_read_only_result_runs', 'write_handler_executions',
              'feature_report_sha256', 'observations', 'read_executed_runs', 'answer_label_not_blocked_runs',
              'texts_not_measured', 'guard_never_exercised', 'texts_without_guard_observation',
              'guard_observed_valid_runs_per_text', 'succeeded_runs', 'status_and_code_distribution',
              'gate_sentence', 'requested_route', 'observed_route', 'outcome_class', 'response_status',
              'error_code', 'guard', 'exit')
# Measurements of a case that the gate summary of the INDEX repeats, so the reviewer sees them next to the verdict.
GATE_MEASUREMENTS = ('read_executed_runs', 'answer_label_not_blocked_runs', 'texts_not_measured',
                     'guard_never_exercised', 'texts_without_guard_observation', 'guard_distribution',
                     'succeeded_runs', 'outcome_distribution')
EXIT_PASS, EXIT_FAIL, EXIT_STOPPED, EXIT_NOT_RUN_LEGS = 0, 1, 2, 3


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
    parser.add_argument('--confirm-spend', action='store_true',
                        help='required for every run that can make a provider call, a pilot included '
                             '(--estimate-only and --dry-run-scripted are exempt)')
    parser.add_argument('--accept-not-run', action='append', default=[], metavar='LEG',
                        help='a required leg that is consciously accepted as NOT_RUN (for example '
                             'f_classification_timeout); without it a NOT_RUN leg makes the exit code 3')
    parser.add_argument('--allow-untracked', action='append', default=[], metavar='PATH',
                        help='an untracked file (repository-relative; a trailing / allows a directory) that does '
                             'not make the tree dirty for a gate-protocol run; default none')
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


def plan_lines(arguments, cases, launcher_replaced: bool) -> list:
    """The printed plan: what will run, what is gating, and what the held-out sets are."""
    gate, reasons = g.gate_protocol(arguments, launcher_replaced)
    gating = [case for case in cases if case in g.GATE_CASES]
    informational = [case for case in cases if case not in g.GATE_CASES]
    heldout = ('RUN, ' + str(arguments.heldout_runs) + ' runs per paraphrase' if arguments.heldout
               else 'NOT RUN (pass --heldout to run them)')
    return [
        f"PLAN transport {arguments.transport}, model {arguments.model}, seed {arguments.seed}, workers {arguments.workers}",
        f"PLAN gating cases, in order: {' '.join(gating) or 'none'}",
        f"PLAN informational cases (reported, never gating): {' '.join(informational) or 'none'}",
        f"PLAN held-out sets (CAP-01-HELDOUT, CAP-02-HELDOUT): {heldout}. They are informational: they never "
        "change a gate verdict or the exit code.",
        f"PLAN repetitions: {arguments.runs} per CAP paraphrase, {arguments.soc_runs} per SOC-01 text, "
        f"{arguments.write_runs} per write-attempt text",
        'PLAN protocol: ' + ('GATE PROTOCOL' if gate else 'PILOT, not gate evidence (' + '; '.join(reasons) + ')'),
        'PLAN legs accepted as NOT_RUN: ' + (' '.join(sorted(arguments.accept_not_run)) or 'none')
        + ('' if arguments.timeout_fault_env or 'SOC-01' not in cases else
           f' (SOC-01 leg {g.FAULT_LEG} will be NOT_RUN: no --timeout-fault-env was given)'),
        'PLAN untracked files allowed in the tree: ' + (' '.join(sorted(arguments.allow_untracked)) or 'none'),
    ]


def not_run_legs(summary: dict) -> dict:
    """Every required leg that did not run, by case: ``{'SOC-01': {leg: reason}}``."""
    return {case: dict(brief['not_run_legs']) for case, brief in sorted(summary.items())
            if case in g.GATE_CASES and brief.get('not_run_legs')}


def gate_summary(summary: dict, accepted=()) -> dict:
    """The verdict of every gate with what the reviewer must see next to it (audit 3 findings H1, H2, H4).

    NOT_RUN: a case of the gate did not run. FAIL: a case failed. PASS_WITH_NOT_RUN_LEGS: every case passed
    but a required leg of one of them did not run; it is never printed as PASS, whether or not the leg was
    accepted. PASS: every case passed and every required leg ran."""
    missing = not_run_legs(summary)
    gates = {}
    for name, needed in GATES.items():
        legs = {f'{case}:{leg}': reason for case in needed for leg, reason in (missing.get(case) or {}).items()}
        if not all(case in summary for case in needed):
            verdict = 'NOT_RUN'
        elif not all(summary[case]['pass'] for case in needed):
            verdict = 'FAIL'
        else:
            verdict = 'PASS_WITH_NOT_RUN_LEGS' if legs else 'PASS'
        gates[name] = {'verdict': verdict, 'cases': list(needed), 'not_run_legs': legs,
                       'not_run_legs_accepted': sorted(leg for leg in legs if leg.split(':', 1)[1] in accepted),
                       'not_run_legs_not_accepted': sorted(leg for leg in legs if leg.split(':', 1)[1] not in accepted),
                       'measurements': {case: {key: summary[case][key] for key in GATE_MEASUREMENTS if key in summary[case]}
                                        for case in needed if case in summary}}
    return gates


def run_verdict(gate_protocol: bool, run_pass: bool, gate_reasons, gates: dict) -> str:
    legs = sorted(leg for item in gates.values() for leg in item['not_run_legs'])
    if not gate_protocol:
        return 'NOT_GATE_EVIDENCE: ' + ('; '.join(gate_reasons) or 'the run did not complete')
    if not run_pass:
        return 'GATE_PROTOCOL_FAIL'
    return ('GATE_PROTOCOL_PASS_WITH_NOT_RUN_LEGS: ' + ', '.join(legs)) if legs else 'GATE_PROTOCOL_PASS'


def exit_code(run_pass: bool, gates: dict) -> int:
    """0 only when the run passed and no NOT_RUN leg is left unaccepted (audit 3 finding H4)."""
    if not run_pass:
        return EXIT_FAIL
    return EXIT_NOT_RUN_LEGS if any(item['not_run_legs_not_accepted'] for item in gates.values()) else EXIT_PASS


def social_table_preflight(transport: str, model: str) -> dict:
    """Before any spend, with no provider configured: every text of the D1 legs must be answered as a
    GREETING by the product's table, and no text of a model leg or of the write attempts may be. A dataset
    that no longer matches the table (the table changed in fix round 8) would waste the paid legs."""
    soc, write = g._dataset('soc01_gate.json'), g._dataset('write_attempts.json')
    base = Path(tempfile.mkdtemp(prefix='quati-eval-table-'))
    try:
        profile = h.Profile(base / 'TABLE', transport, model, provider_configured=False)
        profile.root.mkdir(parents=True)
        init_exit = profile.cli('init', '--json')[0]

        def greeted(text):
            code, value, _ = profile.cli('ask', text, '--json')
            data = value.get('data') if isinstance(value.get('data'), dict) else {}
            return code == 0 and value.get('status') == 'SUCCEEDED' and data.get('result_kind') == 'GREETING'
        table = sorted({text for leg in g.D1_LEGS for text in soc['legs'][leg]['texts']})
        other = sorted({text for leg in (*g.MODEL_LEGS, g.FAULT_LEG) for text in soc['legs'][leg]['texts']}
                       | {item['text'] for item in write['utterances']})
        not_in_table = [text for text in table if not greeted(text)]
        in_table = [text for text in other if greeted(text)]
        return {'pass': init_exit == 0 and not not_in_table and not in_table, 'init_exit': init_exit,
                'table_texts': len(table), 'model_texts': len(other),
                'd1_texts_the_table_does_not_answer': not_in_table, 'model_texts_the_table_answers': in_table}
    finally:
        shutil.rmtree(base, ignore_errors=True)


def main(argv=None):
    arguments = parse(argv)
    if any('=' not in item for item in arguments.timeout_fault_env):
        raise SystemExit('--timeout-fault-env takes NAME=VALUE')
    if arguments.dry_run_scripted:
        h.LAUNCHER, h.ALLOW_LIVE = (sys.executable, str(DRY_RUN_LAUNCHER)), False  # the venv interpreter
        arguments.judge_model = ''  # the judge is a real model: a dry run never calls it
        arguments.transport, arguments.model = DRY_RUN_ROUTE
    launcher_replaced = h.LAUNCHER is not None
    cases = list(arguments.cases) + (['CAP-01-HELDOUT', 'CAP-02-HELDOUT'] if arguments.heldout else [])
    estimate = g.estimate_calls(arguments)
    for line in plan_lines(arguments, cases, launcher_replaced):
        print(line, flush=True)
    print('ESTIMATE ' + json.dumps(estimate, sort_keys=True), flush=True)
    print(f"ESTIMATE provider calls: typical {estimate['typical_calls']}, ceiling {estimate['max_calls']}; cost at "
          f"the haiku rate of the gate6 run: typical about US${estimate['usd_typical_at_haiku_rate']:.2f}, ceiling "
          f"about US${estimate['usd_ceiling_at_haiku_rate']:.2f} (probe calls priced at the ask rate; the judge "
          'model costs more per call)', flush=True)
    if arguments.estimate_only:
        return EXIT_PASS
    # The spend confirmation depends on what was asked for, not on which launcher answers: every run that
    # could reach a provider needs it, a pilot included (audit 3 finding H9). Only the scripted dry run,
    # which this module itself makes network-free, is exempt.
    if not arguments.dry_run_scripted and not arguments.confirm_spend:
        print('STOPPED: a run that can make a provider call needs --confirm-spend (nothing was run, no evidence '
              'was written). --estimate-only and --dry-run-scripted need no confirmation.')
        return EXIT_STOPPED
    run_id = f'{h.now_id()}-{arguments.transport}-{arguments.model}{("-" + arguments.label) if arguments.label else ""}'
    vendor = ({'version': 'NOT_RECORDED', 'reason': 'launcher replaced or --vendor-cli none'}
              if launcher_replaced or arguments.vendor_cli == 'none' else g.vendor_cli_version(arguments.transport))
    # Pre-registration (TEST_EXECUTION_PROTOCOL): everything that fixes the run is hashed before the first
    # provider call, so scoring cannot silently change after results are seen. Nothing here calls a model.
    product = g.product_preflight(arguments.transport, arguments.model)
    prereg = g.preregistration(arguments, run_id, cases, Path(__file__), vendor, launcher_replaced,
                               git=g.git_state(allow_untracked=arguments.allow_untracked), product=product)
    # What was asked for decides the refusal, like the spend confirmation: a gate-protocol command line.
    refusals = g.protocol_refusals(prereg) if g.gate_protocol(arguments)[0] and not arguments.dry_run_scripted else []
    if refusals:
        print('GATE_PROTOCOL_REFUSED ' + json.dumps(refusals, sort_keys=True))
        print('STOPPED before any provider call: a gate-protocol run needs a clean, pre-registrable tree '
              '(nothing was run, no evidence was written).')
        return EXIT_STOPPED
    if 'SOC-01' in cases:
        table = social_table_preflight(arguments.transport, arguments.model)
        prereg['social_table_preflight'] = table
        if not table['pass']:
            print('SOCIAL_TABLE_PREFLIGHT_FAILED ' + json.dumps(table, sort_keys=True, ensure_ascii=False))
            print('STOPPED before any provider call: the SOC-01 dataset does not match the social table of the '
                  'product, so the paid legs would measure the wrong thing.')
            return EXIT_STOPPED
    expected_digest, expected_assets = prereg['code_digest_src_quati'], g.registered_asset_digest(product)
    if not arguments.skip_binding_preflight:
        preflight = g.binding_preflight(arguments.transport, arguments.model, expected_digest, arguments.binding_scope,
                                        expected_assets)
        if not preflight['pass']:
            print('BINDING_PREFLIGHT_FAILED ' + json.dumps(
                {key: preflight[key] for key in ('scope', 'receipts', 'missing', 'mismatched', 'unreadable',
                                                 'asset_missing', 'asset_mismatched', 'missing_by_kind', 'steps')},
                sort_keys=True))
            print('STOPPED before any provider call: a receipt written without a provider does not carry the '
                  'pre-registered code digest (or the pre-registered asset digest of the product), so the run could '
                  'not pass its binding check.')
            return EXIT_STOPPED

    out = Path(arguments.out) if arguments.out else h.ROOT / 'evidence' / 'S00' / f'T05-{run_id}'
    out.mkdir(parents=True)
    base = Path(tempfile.mkdtemp(prefix='quati-eval-'))
    h.REDACTIONS[:] = [(str(base), '<EVAL_PROFILES>'), (str(h.ROOT), '<REPO>'), (str(Path.home()), '<HOME>'),
                       *([(os.environ['USER'], '<USER>')] if len(os.environ.get('USER', '')) >= 4 else [])]
    gate, gate_reasons = prereg['gate_protocol_requested'], prereg['gate_protocol_reasons']
    accepted = sorted(arguments.accept_not_run)
    index = {'run_id': run_id, 'transport': arguments.transport, 'model': arguments.model,
             'runs_per_utterance': arguments.runs, 'soc_runs': arguments.soc_runs, 'write_runs': arguments.write_runs,
             'seed': arguments.seed, 'judge_model': arguments.judge_model, 'cases': cases,
             'gate_protocol_requested': gate, 'gate_protocol_reasons': gate_reasons,
             'launcher_replaced': launcher_replaced, 'harness_sha256': prereg['harness_sha256'], 'files': {},
             'heldout': {'run': bool(arguments.heldout), 'gating': False,
                         'note': 'The held-out sets are informational: they never change a gate verdict or the exit code.'},
             'accept_not_run': accepted, 'estimate': {key: estimate[key] for key in (
                 'typical_calls', 'max_calls', 'usd_typical_at_haiku_rate', 'usd_ceiling_at_haiku_rate')},
             'summary': {}, 'launched_violations': [], 'cases_completed': []}
    index['preregistration_sha256'] = h.write_evidence(out, 'PREREG.json', prereg)
    doctors = []
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
            doctors += [(f'{case}{where}', identity) for where, identity in g.doctor_responses(result)]
            index['cases_completed'].append(case)
            print(json.dumps(brief, sort_keys=True, default=str), flush=True)
    finally:
        summary = index['summary']
        index['binding'] = g.receipt_binding(base, expected_digest, arguments.binding_scope, expected_assets)
        index['doctor_binding'] = g.doctor_binding(doctors, product.get('behavior'))
        index['provider_calls_observed'] = g.observed_calls(base)
        completed = all(case in summary for case in cases)
        # gate_protocol is true only when the full gate case list ran, to the end, with the gate repetitions.
        index['gate_protocol'] = bool(gate and completed)
        gating_failed = sorted(case for case in cases if case in g.GATE_CASES and not summary.get(case, {}).get('pass'))
        index['gating_cases_failed'] = gating_failed
        index['run_pass'] = bool(completed and not gating_failed and index['binding']['pass']
                                 and index['doctor_binding']['pass'] and not index['launched_violations'])
        index['gate_summary'] = gate_summary(summary, accepted)
        index['gates'] = {name: item['verdict'] for name, item in index['gate_summary'].items()}
        index['not_run_legs'] = not_run_legs(summary)
        index['not_run_legs_not_accepted'] = sorted(leg for item in index['gate_summary'].values()
                                                    for leg in item['not_run_legs_not_accepted'])
        index['accept_not_run_unused'] = sorted(set(accepted) - {leg for legs in index['not_run_legs'].values() for leg in legs})
        index['verdict'] = run_verdict(index['gate_protocol'], index['run_pass'], gate_reasons, index['gate_summary'])
        index['exit_code'] = exit_code(index['run_pass'], index['gate_summary'])
        index['index_note'] = ('Gate protocol: 10 paraphrases x 3 runs per selection case, SOC-01 legs with at least '
                               '10 runs per text, write attempts with at least 5 runs per text. The verdict is input '
                               'for the independent audit and never a seal.' if index['gate_protocol'] else
                               'Pilot or partial run (not gate evidence).')
        h.write_evidence(out, 'INDEX.json', index)
        if not arguments.keep_profiles:
            shutil.rmtree(base, ignore_errors=True)
    for name, item in index['gate_summary'].items():
        print(f"GATE {name}: {item['verdict']}"
              + (f"; NOT_RUN legs: {json.dumps(item['not_run_legs'], sort_keys=True)}; accepted with --accept-not-run: "
                 f"{item['not_run_legs_accepted'] or 'none'}" if item['not_run_legs'] else '')
              + f"; measurements {json.dumps(item['measurements'], sort_keys=True, ensure_ascii=False)}", flush=True)
    print(json.dumps({key: index[key] for key in ('verdict', 'run_pass', 'gates', 'gating_cases_failed',
                                                  'not_run_legs_not_accepted', 'exit_code')}
                     | {'binding': {key: index['binding'][key] for key in ('pass', 'scope', 'receipts', 'missing',
                                                                           'mismatched', 'asset_missing',
                                                                           'asset_mismatched', 'missing_by_kind')},
                        'doctor_binding': {key: index['doctor_binding'][key] for key in (
                            'pass', 'doctor_responses', 'offenders_total', 'asset_digest')},
                        'provider_calls_observed': index['provider_calls_observed'],
                        'launched_violations': len(index['launched_violations'])}, sort_keys=True))
    print(f'EVIDENCE {out}')
    return index['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
