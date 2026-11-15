"""Offline verification of normative spec completeness and JSON schemas only."""
from pathlib import Path
import json,re,sys,yaml
from jsonschema import Draft202012Validator
from behavior_compiler import ROOT,validate_machine,validate_behavior,load_yaml

def main():
    for sf in (ROOT/'contracts').glob('*.schema.json'):
        Draft202012Validator.check_schema(json.loads(sf.read_text(encoding='utf-8')))
    for f in (ROOT/'examples/statecharts').glob('*.yaml'): validate_machine(load_yaml(f))
    for f in (ROOT/'examples/behavior').glob('*.yaml'):validate_behavior(load_yaml(f))
    cap=json.loads((ROOT/'examples/capabilities/example_analytic_research.json').read_text(encoding='utf-8'))
    schema=json.loads((ROOT/'contracts/scs-capability.schema.json').read_text(encoding='utf-8'))
    Draft202012Validator(schema).validate(cap)
    for f in (ROOT/'docs/prds').glob('M??.md'):
        text=f.read_text(encoding='utf-8')
        if not all(x in text for x in ('Normative requirements','Observable acceptance tests','Threat model')):
            raise ValueError('Missing unique module PRD sections: '+str(f))
    if len(list((ROOT/'docs/prds').glob('M??.md')))!=31:raise ValueError('Expected 31 module PRDs')
    if len(list((ROOT/'docs/redteam/modules').glob('M??_REDTEAM.md')))!=31:raise ValueError('Expected 31 module threat sheets')
    if any('not implemented' not in (ROOT/'README.md').read_text(encoding='utf-8').lower() for _ in [0]):
        raise ValueError('Must disclose implementation status')
    print('L0 SPEC VALIDATION: PASS (schemas, machines, example, 31 PRDs and 31 red teams). NO APP RUNTIME PROOF.')
if __name__=='__main__':main()
