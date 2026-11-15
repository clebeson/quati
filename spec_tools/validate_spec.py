"""L0 specification consistency checks; no runtime or provider certification."""
from pathlib import Path
import csv
import json
import re
from jsonschema import Draft202012Validator
from behavior_compiler import ROOT, validate_machine, validate_behavior, validate_schema, load_yaml


def main():
    for path in sorted((ROOT / 'contracts').glob('*.schema.json')):
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding='utf-8')))
    for path in sorted((ROOT / 'examples/statecharts').glob('*.yaml')):
        validate_machine(load_yaml(path))
    for path in sorted((ROOT / 'examples/behavior').glob('*.yaml')):
        receipt, _ = validate_behavior(load_yaml(path))
        validate_schema(receipt, 'prompt-build-receipt.schema.json')
    for path in sorted((ROOT / 'examples/capabilities').glob('*.json')):
        validate_schema(json.loads(path.read_text()), 'scs-capability.schema.json')
    for path in sorted((ROOT / 'examples/payloads').glob('classification_*.json')):
        validate_schema(json.loads(path.read_text()), 'request-classification.schema.json')
    expected, prompt = validate_behavior(load_yaml(ROOT / 'examples/behavior/executive-secretary.yaml'))
    actual = json.loads((ROOT / 'examples/behavior/compiled_receipt.reference.json').read_text())
    validate_schema(actual, 'prompt-build-receipt.schema.json')
    if actual != expected:
        raise ValueError('Reference receipt is stale')
    if (ROOT / 'examples/behavior/prompt_preview.reference.txt').read_text() != 'REFERENCE OUTPUT ONLY — NOT A PRODUCTION PROMPT\n\n' + prompt + '\n':
        raise ValueError('Reference prompt is stale')
    state_schema = json.loads((ROOT / 'contracts/commitment.schema.json').read_text())
    machine = load_yaml(ROOT / 'examples/statecharts/commitment.yaml')
    if set(state_schema['properties']['state']['enum']) != set(machine['states']):
        raise ValueError('Commitment contract differs from reference states')
    prds = sorted((ROOT / 'docs/prds').glob('M??.md'))
    threats = sorted((ROOT / 'docs/redteam/modules').glob('M??_REDTEAM.md'))
    if len(prds) != 31 or len(threats) != 31:
        raise ValueError('Expected 31 PRDs and 31 threat sheets')
    corpus = '\n'.join(path.read_text() for path in prds + threats)
    for path in prds:
        if not all(section in path.read_text() for section in ('Normative requirements', 'Observable acceptance tests', 'Threat model')):
            raise ValueError('Missing PRD sections: ' + str(path))
    rows = list(csv.DictReader((ROOT / 'docs/traceability/REQUIREMENTS.csv').open()))
    ids = [row['id'] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate requirement IDs')
    for row in rows:
        if row['id'] not in corpus:
            raise ValueError('Requirement absent from source: ' + row['id'])
        for column in ('acceptance_ref', 'redteam_ref'):
            for ref in re.split(r'[;|/]', row[column]):
                if ref and ref not in corpus:
                    raise ValueError('Missing trace reference: ' + ref)
        if not (ROOT / 'docs/implementation/SLICES' / (row['slice'] + '.md')).is_file():
            raise ValueError('Unknown slice: ' + row['slice'])
    for relative, column in [('docs/testing/TEST_LEDGER.csv', 'case_id'), ('docs/redteam/RISK_REGISTER.csv', 'risk_id')]:
        records = list(csv.DictReader((ROOT / relative).open()))
        keys = [item[column] for item in records]
        if len(keys) != len(set(keys)):
            raise ValueError('Duplicate IDs in ' + relative)
    seeds = [json.loads(line) for line in (ROOT / 'evals/seed_eri.jsonl').read_text().splitlines() if line.strip()]
    if len({case['case_id'] for case in seeds}) != len(seeds):
        raise ValueError('Duplicate evaluation cases')
    print('L0 SPEC VALIDATION: PASS (contracts, examples, reference freshness, states, requirement references). NO APP RUNTIME PROOF.')


if __name__ == '__main__':
    main()
