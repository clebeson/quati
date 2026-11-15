"""S00 runtime static compiler; authorization is separately enforced by domain policy.

Only validates and renders authorized declarative files; it does not invoke models,
execute guards, start DBOS, write production policy or prove agent competence.
"""
from __future__ import annotations
import argparse,hashlib,json,sys,re
from datetime import datetime
from collections import defaultdict, deque
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator, FormatChecker, SchemaError

ROOT=Path(__file__).resolve().parents[1] / 'assets'
FORMATS = FormatChecker()
@FORMATS.checks('date-time')
def _timestamp(value):
    if not isinstance(value, str):
        return True
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})', value):
        return False
    try:
        return datetime.fromisoformat(value.upper().replace('Z', '+00:00')).tzinfo is not None
    except ValueError:
        return False

GUARDS=frozenset({'always','authorized_request','safe_to_begin','under_budget','valid_feedback','under_reinvestigation_budget','has_evidence','delivery_acknowledged'})
ACTIONS=frozenset({'record_classification','commit_receipt','record_cancel','start_work','record_progress','ask_user','merge_context','review_evidence','deepen_work','prepare_delivery','prepare_partial_delivery','record_blocker','resume_work','record_delivery'})

def digest(value):
    raw=json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()
    return hashlib.sha256(raw).hexdigest()

COMPILER_VERSION = '1.1.0'
TRUSTED_POLICY = {
    'id': 'trusted_policy/default', 'version': '1.0.0',
    'invariants': ['authenticated_identity', 'authorization_before_effect',
                   'durable_commitment_before_receipt', 'evidence_before_completion',
                   'acknowledgement_before_delivery', 'no_self_granted_permissions'],
}

class UniqueKeyLoader(yaml.SafeLoader):
    """Reject ambiguous declarative mappings, including duplicate YAML keys."""

def _unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise ValueError('YAML mapping keys must be strings')
        if key in result:
            raise ValueError('Duplicate YAML key: ' + key)
        result[key] = loader.construct_object(value_node, deep=deep)
    return result

UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping)

def load_yaml(path):
    try:
        data=yaml.load(Path(path).read_text(encoding='utf-8'), Loader=UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise ValueError('Invalid declarative YAML') from exc
    if not isinstance(data,dict): raise ValueError('YAML document must be a mapping')
    return data

def validate_schema(document,schema_file):
    schema=json.loads((ROOT/'contracts'/schema_file).read_text(encoding='utf-8'))
    Draft202012Validator.check_schema(schema)
    problems=sorted(Draft202012Validator(schema, format_checker=FORMATS).iter_errors(document),key=lambda e:list(map(str,e.path)))
    if problems: raise ValueError('Schema error: '+problems[0].message)
    if schema_file == 'scs-capability.schema.json':
        for field in ('input_schema', 'output_schema'):
            nested = document[field]
            try:
                Draft202012Validator.check_schema(nested)
            except SchemaError as exc:
                raise ValueError('Invalid embedded ' + field) from exc
            def check_refs(value):
                if isinstance(value, dict):
                    for key, item in value.items():
                        if key in ('$ref', '$dynamicRef') and not item.startswith('#'):
                            raise ValueError('Embedded schemas permit local references only')
                        check_refs(item)
                elif isinstance(value, list):
                    for item in value:
                        check_refs(item)
            check_refs(nested)
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
        # Protected stages cannot be bypassed by recombining registered names.
        # This is static semantics, not proof that runtime guards are enforced.
        protected_incoming = {
            'CLASSIFIED': {('RECEIVED', 'authorized_request', 'record_classification'),
                           ('INPUT_RECEIVED', 'authorized_request', 'record_classification'),
                           ('WAIT', 'under_budget', 'merge_context')},
            'ACKNOWLEDGED': {('CLASSIFIED', 'authorized_request', 'commit_receipt')},
            'EVIDENCE_REVIEW': {('IN_PROGRESS', 'under_budget', 'review_evidence')},
            'READY_TO_DELIVER': {('EVIDENCE_REVIEW', 'has_evidence', 'prepare_delivery'),
                                 ('EVIDENCE_REVIEW', 'has_evidence', 'prepare_partial_delivery')},
            'DELIVERED': {('READY_TO_DELIVER', 'delivery_acknowledged', 'record_delivery')},
            'REGISTER_WORK': {('CLASSIFIED', 'safe_to_begin', 'commit_receipt'),
                              ('ASK_CLARIFICATION', 'safe_to_begin', 'commit_receipt')},
        }
        incoming = (t['source'], t['guard'], t['action'])
        if t['target'] in protected_incoming and incoming not in protected_incoming[t['target']]:
            raise ValueError('Protected state transition violates control semantics')
        protected_actions = {
            'commit_receipt': {('CLASSIFIED', 'ACKNOWLEDGED', 'authorized_request'),
                               ('CLASSIFIED', 'REGISTER_WORK', 'safe_to_begin'),
                               ('ASK_CLARIFICATION', 'REGISTER_WORK', 'safe_to_begin')},
            'record_delivery': {('READY_TO_DELIVER', 'DELIVERED', 'delivery_acknowledged'),
                                ('RESPOND', 'CLOSED', 'always')},
            'prepare_partial_delivery': {('EVIDENCE_REVIEW', 'READY_TO_DELIVER', 'has_evidence')},
        }
        action_edge = (t['source'], t['target'], t['guard'])
        if t['action'] in protected_actions and action_edge not in protected_actions[t['action']]:
            raise ValueError('Protected action cannot be retargeted')
        if t['target'] == 'CANCELLED' and t['action'] != 'record_cancel':
            raise ValueError('Protected cancellation action required')
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
    if not machine_file.resolve().is_relative_to(ROOT.resolve()) or not machine_file.is_file():
        raise ValueError('Statechart must resolve to a file inside specification root')
    machine=load_yaml(machine_file);state_meta=validate_machine(machine)
    if profile['execution']['max_investigation_loops'] > machine['budget']['max_reinvestigations']:
        raise ValueError('Behavior investigation budget exceeds statechart budget')
    # Config text is data and grants no authority. Runtime must enforce limits.
    limits = {**profile['context'],
              'max_investigation_loops': profile['execution']['max_investigation_loops'],
              'max_transitions': machine['budget']['max_transitions']}
    language = ('Reply in language tag ' + profile['interaction']['language_override']
                if profile['interaction']['language_policy'] == 'explicit_override'
                else 'Reply in the requester language.')
    # This preview never interpolates executable code, secrets, or untrusted tools.
    prompt='\n'.join([
      'Protected SECMA invariants: never bypass identity, approval, durable commitments or evidence gates.',
      'Role: '+profile['role'].strip(),
      'Interaction verbosity: '+profile['interaction']['verbosity'],
      'Interaction cadence: '+profile['interaction']['cadence'],
      'Clarification style: '+profile['interaction']['clarification_style'],
      'Do not claim action until recorded.',
      'Execution depth: '+profile['execution']['default_depth'],
      'Safe read ahead: '+str(profile['execution']['safe_read_ahead']).lower(),
      'Specialist model role: '+profile['models']['specialist_role'],
      'Effective limits: '+json.dumps(limits, sort_keys=True),
      language,
      'This prompt does not grant rights; all actions pass trusted code authorization.'
    ])
    return {'compiler_version': COMPILER_VERSION, 'policy_ref': TRUSTED_POLICY['id'],
        'policy_hash': digest(TRUSTED_POLICY),
        'source_versions': {'behavior': profile['version'], 'statechart': machine['version']},
        'effective_limits': limits,
        'behavior_id':profile['id'],'behavior_version':profile['version'],
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
