"""OFFLINE specification reference compiler/validator, NOT the SECMA runtime.

Only validates and renders authorized declarative files; it does not invoke models,
execute guards, start DBOS, write production policy or prove agent competence.
"""
from __future__ import annotations
import argparse,hashlib,json,sys
from collections import defaultdict, deque
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[1]
GUARDS=frozenset({'always','authorized_request','safe_to_begin','under_budget','valid_feedback','under_reinvestigation_budget','has_evidence','delivery_acknowledged'})
ACTIONS=frozenset({'record_classification','commit_receipt','record_cancel','start_work','record_progress','ask_user','merge_context','review_evidence','deepen_work','prepare_delivery','prepare_partial_delivery','record_blocker','resume_work','record_delivery'})

def digest(value):
    raw=json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()
    return hashlib.sha256(raw).hexdigest()

def load_yaml(path):
    data=yaml.safe_load(Path(path).read_text(encoding='utf-8'))
    if not isinstance(data,dict): raise ValueError('YAML document must be a mapping')
    return data

def validate_schema(document,schema_file):
    schema=json.loads((ROOT/'contracts'/schema_file).read_text(encoding='utf-8'))
    Draft202012Validator.check_schema(schema)
    problems=sorted(Draft202012Validator(schema).iter_errors(document),key=lambda e:list(map(str,e.path)))
    if problems: raise ValueError('Schema error: '+problems[0].message)
    return True

def validate_machine(machine):
    validate_schema(machine,'statechart.schema.json')
    states=set(machine['states']);term=set(machine['terminal']);initial=machine['initial']
    if initial not in states or not term <= states: raise ValueError('Initial/terminal states must exist')
    if initial in term:raise ValueError('Initial state cannot be terminal for this reference compiler')
    transitions=machine['transitions'];edges=defaultdict(list);seen=set()
    for t in transitions:
        if t['source'] not in states or t['target'] not in states: raise ValueError('Unknown transition state')
        if t['source'] in term: raise ValueError('Terminal states must not have outgoing edges')
        if t['guard'] not in GUARDS: raise ValueError('Unregistered guard: '+t['guard'])
        if t['action'] not in ACTIONS: raise ValueError('Unregistered action: '+t['action'])
        key=(t['source'],t['event'])
        if key in seen: raise ValueError('Ambiguous transition for event: '+str(key))
        seen.add(key);edges[t['source']].append(t['target'])
    def walk(start,ed):
        found={start};q=deque([start]);
        while q:
            for n in ed[q.popleft()]:
                if n not in found:found.add(n);q.append(n)
        return found
    reachable=walk(initial,edges)
    if reachable!=states: raise ValueError('Unreachable states: '+str(sorted(states-reachable)))
    reverse=defaultdict(list)
    for s,targets in edges.items():
        for target in targets:reverse[target].append(s)
    can_finish=set()
    for terminal in term:can_finish.update(walk(terminal,reverse))
    if can_finish!=states:raise ValueError('Dead-end states: '+str(sorted(states-can_finish)))
    if machine['budget']['max_transitions']<len(states):raise ValueError('Insufficient transition budget')
    return {'machine_hash':digest(machine),'state_count':len(states),'transition_count':len(transitions)}

def validate_behavior(profile):
    validate_schema(profile,'behavior-package.schema.json')
    if profile['policy_ref']!='trusted_policy/default':
        raise ValueError('Unapproved policy ref: '+profile['policy_ref'])
    machine_file=ROOT/profile['statechart_ref']
    if not machine_file.is_file() or not machine_file.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError('Statechart must resolve to a file inside specification root')
    machine=load_yaml(machine_file);state_meta=validate_machine(machine)
    # This preview never interpolates executable code, secrets, or untrusted tools.
    prompt='\n'.join([
      'Protected SECMA invariants: never bypass identity, approval, durable commitments or evidence gates.',
      'Role: '+profile['role'].strip(),
      'Interaction verbosity: '+profile['interaction']['verbosity'],
      'Interaction cadence: '+profile['interaction']['cadence'],
      'Ask only value-positive or blocking questions; do not claim action until recorded.',
      'Execution depth: '+profile['execution']['default_depth'],
      'Reply in the requester language unless an explicit language override is present.',
      'This prompt does not grant rights; all actions pass trusted code authorization.'
    ])
    return {'behavior_id':profile['id'],'behavior_version':profile['version'],
        'behavior_hash':digest(profile),'statechart_hash':state_meta['machine_hash'],
        'prompt_hash':hashlib.sha256(prompt.encode()).hexdigest(),
        'sections':['kernel_invariants','role','interaction','execution','language'],
        'token_budget':profile['context']['max_context_tokens'],
        'model_profile_ref':profile['models']['router_role']},prompt

def render_mermaid(machine):
    validate_machine(machine)
    out=['stateDiagram-v2','    [*] --> '+machine['initial']]
    for t in machine['transitions']:
        out.append(f"    {t['source']} --> {t['target']}: {t['event']} [{t['guard']}]")
    for s in machine['terminal']:out.append('    '+s+' --> [*]')
    return '\n'.join(out)+'\n'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['validate','render','receipt'])
    p.add_argument('file')
    a=p.parse_args();d=load_yaml(a.file)
    if a.command=='validate':
        if 'transitions' in d: print(json.dumps(validate_machine(d),sort_keys=True))
        else: print(json.dumps(validate_behavior(d)[0],sort_keys=True))
    elif a.command=='render': print(render_mermaid(d),end='')
    else:
        rec,prompt=validate_behavior(d)
        print(json.dumps({'receipt':rec,'preview':prompt},indent=2))
if __name__=='__main__':main()
