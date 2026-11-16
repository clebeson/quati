"""Run the S00 blind live evaluation and write evidence/S00/T05-<run-id>/.

Spends real money on the operator's own provider sign-in. Example:

    .venv/bin/python tests/evals/run_live_eval.py --transport claude_cli --model haiku \
        --cases CAP-01 CAP-02 --runs 3 --workers 4 --judge-model sonnet

`--runs 3` over 10 paraphrases is the gate protocol (N=30 per case). A pilot uses `--runs 1`
and is never gate evidence (its summary says so).
"""
import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import live_harness as h  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--transport', default='claude_cli')
    parser.add_argument('--model', default='haiku')
    parser.add_argument('--cases', nargs='+', default=['CAP-01', 'CAP-02', 'CAP-03', 'CAP-05', 'SOC-01', 'BEH'])
    parser.add_argument('--runs', type=int, default=3)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--seed', type=int, default=20261116)
    parser.add_argument('--judge-model', default='sonnet')
    parser.add_argument('--label', default='')
    parser.add_argument('--keep-profiles', action='store_true')
    args = parser.parse_args(argv)

    run_id = f'{h.now_id()}-{args.transport}-{args.model}{("-" + args.label) if args.label else ""}'
    out = h.ROOT / 'evidence' / 'S00' / f'T05-{run_id}'
    out.mkdir(parents=True)
    base = Path(tempfile.mkdtemp(prefix='quati-eval-'))
    index = {'run_id': run_id, 'transport': args.transport, 'model': args.model, 'runs_per_utterance': args.runs,
             'seed': args.seed, 'gate_protocol': args.runs == 3, 'judge_model': args.judge_model,
             'harness_sha256': h.sha256_file(Path(h.__file__)), 'files': {}}
    # Pre-registration (TEST_EXECUTION_PROTOCOL): datasets, harness and system code are hashed and
    # written before the first model call, so scoring cannot silently change after results are seen.
    prereg = {'run_id': run_id, 'written_before_first_call': True, 'harness_sha256': index['harness_sha256'],
              'runner_sha256': h.sha256_file(Path(__file__)),
              'datasets': {p.name: h.sha256_file(p) for p in sorted(h.DATASETS.glob('*.json'))},
              'code_digest_src_quati': h.code_digest(h.SOURCE / 'quati'),
              'behavior_suite_is_post_hoc': True}
    index['preregistration_sha256'] = h.write_evidence(out, 'PREREG.json', prereg)
    try:
        for case in args.cases:
            if case in ('CAP-01', 'CAP-02'):
                result = h.run_selection_case(case, base, args.transport, args.model, args.runs, args.seed, args.workers)
            elif case == 'CAP-03':
                result = h.run_disabled_case(base, args.transport, args.model, args.seed)
            elif case == 'CAP-05':
                result = h.run_unprobed_case(base, args.transport, args.model, args.seed)
            elif case == 'SOC-01':
                result = h.run_social_case(base, args.transport, args.model, args.seed)
            elif case == 'BEH':
                result = h.run_behavior_suite(base, args.transport, args.model, args.judge_model, args.seed, args.workers)
            else:
                raise SystemExit(f'unknown case {case}')
            index['files'][case] = h.write_evidence(out, f'{case}.json', result)
            brief = {k: result.get(k) for k in ('case_id', 'n', 'passed', 'gate_pass', 'wilson95_lower', 'unauthorized_effects',
                                                 'observed_models', 'cost_usd_total_known', 'cost_usd_all_receipts', 'elapsed_s_p50', 'elapsed_s_max',
                                                 'distinct_digest_values', 'pass', 'checks', 'l3_runs') if k in result}
            if result.get('failures'):
                brief['failures'] = result['failures']
            if result.get('per_case'):
                brief['per_case'] = {k: {x: v[x] for x in ('pass', 'status', 'executed', 'judge')} | {
                    'failed': sorted(c for c, ok in v['checks'].items() if not ok)} for k, v in result['per_case'].items()}
            index.setdefault('summary', {})[case] = brief
            print(json.dumps(brief, sort_keys=True, default=str), flush=True)
    finally:
        index['index_note'] = ('Pilot (not gate evidence)' if args.runs != 3 else
                               'Gate protocol: 10 paraphrases x 3 runs per selection case')
        h.write_evidence(out, 'INDEX.json', index)
        if not args.keep_profiles:
            shutil.rmtree(base, ignore_errors=True)
    print(f'EVIDENCE {out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
