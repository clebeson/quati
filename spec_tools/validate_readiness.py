"""L0 specification readiness checks. Never certifies runtime or model behavior."""
from pathlib import Path
import csv
import json
from collections import Counter, defaultdict, deque
from jsonschema import Draft202012Validator
from behavior_compiler import FORMATS
from build_consolidated import build

ROOT=Path(__file__).resolve().parents[1]


def read(path): return json.loads((ROOT/path).read_text())
def require(condition,message):
    if not condition: raise ValueError(message)


def validate_control(table):
    states=set(table['states']); terminal=set(table['terminal']); edges=defaultdict(list); seen=set()
    require(table['initial'] in states and terminal <= states,'Control state identity mismatch')
    for t in table['transitions']:
        require(t['source'] in states and t['target'] in states,'Unknown control state')
        require(t['source'] not in terminal,'Terminal state has outgoing transition')
        key=(t['source'],t['event']); require(key not in seen,'Ambiguous control transition'); seen.add(key)
        edges[t['source']].append(t['target'])
        if t['target']=='DELIVERED': require(t['guard']=='authenticated_current_delivery_receipt','Delivery acknowledgement bypass')
        if t['target']=='SEND_PENDING': require(t['source']=='READY_TO_DELIVER' and t['guard']=='authorized_effect_intent_committed','Dispatch authority bypass')
        if t['target']=='CANCELLED': require(t['guard'] in {'authorized_and_no_accepted_or_pending_effect','all_effects_confirmed_absent_and_dispatch_stopped'},'Unsafe no-effect cancellation')
        if t['target']=='CANCELLED_WITH_EFFECTS': require(t['guard']=='all_effects_reconciled_and_dispatch_stopped','Unreconciled cancellation')
    def walk(start,graph):
        found={start};q=deque([start])
        while q:
            for n in graph[q.popleft()]:
                if n not in found:found.add(n);q.append(n)
        return found
    require(walk(table['initial'],edges)==states,'Unreachable lifecycle state')
    for state in states-terminal:
        require((state,'deadline') in seen,'Missing deadline recovery for '+state)
        require(bool(walk(state,edges)&terminal),'No lifecycle terminal path for '+state)
    require(table['budget']['max_transitions']>0,'Unbounded lifecycle transitions')



def validate_closure(tasks, plans, cases):
    by_task = {t['id']:t for t in tasks}
    by_plan = {p['plan_id']:p for p in plans}
    by_case = {c['case_id']:c for c in cases}
    for p in plans:
        owner = p['test_owner_task']
        require(owner == p['final_gate_task'] and owner in by_task, 'Undefined final test owner')
        require(p['plan_id'] in by_task[owner]['owned_requirement_plan_ids'], 'Requirement test ownership gap')
        require(p['plan_id'] in by_task[owner]['final_acceptance_plan_ids'], 'Final acceptance closure gap')
    for t in tasks:
        expected = {p['plan_id'] for p in plans if p['test_owner_task'] == t['id']}
        require(set(t['owned_requirement_plan_ids']) == expected, 'Task requirement ownership mismatch')
        require(set(t['final_acceptance_plan_ids']) == expected, 'Task final acceptance mismatch')
        require(len(t['local_assertions']) == len(t['done_conditions']), 'Missing local task assertion')
        require({c['case_id'] for c in t['case_execution']} == set(t['test_case_ids']), 'Missing case execution mode')
        for case in t['case_execution']:
            owner = case['full_proof_owner_task']
            require(owner in by_task and by_task[owner]['slice'] == by_case[case['case_id']]['slice'], 'Wrong full-proof case owner')
            expected_mode = 'FULL_REQUIRED' if owner == t['id'] else 'REGRESSION_REUSE_OR_RETEST' if t['id'] > owner else 'CONTRIBUTION_ONLY'
            require(case['mode'] == expected_mode, 'Incorrect contribution/full proof distinction')
        require(t['memory_lookup']['index'] == 'memory/index.json', 'Missing mandatory memory lookup')


GUARD_INPUT_ROOTS = {
    'commitment', 'snapshot_committed', 'event', 'context', 'token_revoked', 'now',
    'active_policy_version', 'policy_decision', 'approval', 'effects', 'attempts',
    'delivery', 'assessment', 'candidate_producer_actor_id', 'evidence',
    'classification', 'budget', 'usage', 'config'}
RECORD_TABLES = {
    'commitments', 'commitment_events', 'effect_intents', 'outbox', 'timer_intents',
    'workflow_refs', 'work_items', 'approval_requests'}


def validate_guard_registry(table, registry, boundaries):
    """The guard/action registry (GUARD_PREDICATES.md) must name exactly the control table's guards and actions."""
    require(registry.get('schema_version') == 'quati-guard-registry/1', 'Guard registry schema_version mismatch')
    guards, actions = registry.get('guards', []), registry.get('actions', [])
    guard_names = [g['name'] for g in guards]
    action_names = [a['name'] for a in actions]
    require(len(guard_names) == len(set(guard_names)), 'Duplicate guard in registry')
    require(len(action_names) == len(set(action_names)), 'Duplicate action in registry')
    require(set(guard_names) == {row['guard'] for row in table['transitions']}, 'Guard registry differs from control table guards')
    require(set(action_names) == {row['action'] for row in table['transitions']}, 'Action registry differs from control table actions')
    codes = set(boundaries['$defs']['Error']['properties']['code']['enum'])
    for g in guards:
        require(set(g) == {'name', 'inputs', 'denial_reason_code', 'description'}, f"Guard {g['name']} has unexpected keys")
        require(g['inputs'] and all(i.split('.')[0] in GUARD_INPUT_ROOTS for i in g['inputs']), f"Guard {g['name']} has an unknown input root")
        require(g['denial_reason_code'] in codes, f"Guard {g['name']} denial code is not an Error.code")
        require(g['description'].strip(), f"Guard {g['name']} lacks a description")
    for a in actions:
        require(set(a) == {'name', 'description', 'records_written'}, f"Action {a['name']} has unexpected keys")
        require({'commitments', 'commitment_events'} <= set(a['records_written']) <= RECORD_TABLES, f"Action {a['name']} writes an unknown record table")
        require(a['description'].strip(), f"Action {a['name']} lacks a description")


def validate_commitment(document):
    Draft202012Validator(read('contracts/commitment-v2.schema.json'),format_checker=FORMATS).validate(document)
    if document['state'] in {'READY_TO_DELIVER','SEND_PENDING','DELIVERED'}:
        require(document['assessed_goal_revision'] == document['goal_revision'], 'Stale goal assessment')


def validate_seal_provenance(seal, root=ROOT):
    import hashlib
    def verify(path, digest):
        target=(root/path).resolve()
        require(target.is_relative_to(root.resolve()), 'Seal path escapes package')
        require(target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest()==digest, 'Stale or missing seal evidence/source/artifact')
    require(set(seal['evidence_refs']) == set(seal['evidence_sha256']), 'Evidence digest coverage mismatch')
    for mapping in ('artifact_sha256','evidence_sha256'):
        for path,digest in seal.get(mapping, {}).items(): verify(path,digest)
    if 'commit_evidence' in seal:
        commit = seal['commit_evidence']
        require({commit['test_log_ref'], commit['transcript_ref']} <= set(seal['evidence_refs']),
                'Test log or transcript is not bound to evidence')
        return
    snapshot=seal['source_snapshot']
    verify(snapshot['manifest_path'],snapshot['manifest_sha256'])
    manifest=json.loads((root/snapshot['manifest_path']).read_text())
    require(manifest.get('schema_version')=='quati-source-snapshot/1' and bool(manifest.get('files')), 'Invalid source snapshot')
    require(set(seal['artifact_sha256']) <= set(manifest['files']), 'Source snapshot omits sealed artifacts')
    for path,digest in manifest['files'].items(): verify(path,digest)


def _resolve_seal_reference(ref, indexed, allowed_scopes, commit):
    import hashlib
    require(indexed['path']==ref['path'] and indexed['record_sha256']==ref['record_sha256'] and indexed['kind']==ref['kind'], 'State and seal index disagree')
    path = (ROOT/ref['path']).resolve()
    require(path.is_relative_to(ROOT.resolve()), 'Seal path escapes package')
    require(path.is_file(), 'Missing seal record')
    require(hashlib.sha256(path.read_bytes()).hexdigest() == ref['record_sha256'], 'Seal record changed')
    seal=json.loads(path.read_text())
    Draft202012Validator(read('state/schemas/governance-seal.schema.json'),format_checker=FORMATS).validate(seal)
    require(ref['scope_id'] in seal['scope_ids'] and ref['kind'] == seal['kind'], 'Seal scope/kind mismatch')
    require(seal['seal_id'] == ref['seal_id'] and ref['scope_id'] in allowed_scopes, 'Seal identity/scope mismatch')
    if 'commit_evidence' in seal:
        require(seal['commit_evidence']['commit_sha'] == commit, 'Seal commit mismatch')
    validate_seal_provenance(seal)
    return seal


def _validate_gate_seals(seals, slice_accepted):
    require(bool(seals), 'PASS gate has no seal references')
    require(all(seal['verdict'] == 'PASS' for seal in seals), 'Nonpassing seal used for PASS gate')
    kinds = {seal['kind'] for seal in seals}
    require({'TESTS_VERIFIED', 'EVIDENCE_VERIFIED'} <= kinds, 'PASS gate lacks mandatory slice seals')
    if slice_accepted:
        require('SLICE_ACCEPTED' in kinds, 'PASS slice lacks SLICE_ACCEPTED seal')
    return {json.dumps(seal.get('commit_evidence', {}).get('commit_sha') or seal['source_snapshot'], sort_keys=True)
            for seal in seals}


def validate_seal_references(state):
    index = read(state['seal_registry_ref'])
    records = {r['seal_id']:r for r in index['records']}
    require(len(records) == len(index['records']), 'Duplicate seal identity')
    for sid, item in state['slices'].items():
        slice_sources = set()
        require(set(item['gate_seal_refs']) == set(item['gates']), 'Missing per-gate seal lookup')
        for gate, status in item['gates'].items():
            seals = []
            for ref in item['gate_seal_refs'][gate]:
                require(ref['seal_id'] in records, 'Seal not in canonical index')
                seals.append(_resolve_seal_reference(ref, records[ref['seal_id']], {sid, gate}, item['commit']))
            if status == 'PASS':
                slice_sources.update(_validate_gate_seals(seals, item['status'] == 'PASS'))
        require(len(slice_sources) <= 1, 'Slice seals reference different source identities')


def main():
    requirements=list(csv.DictReader((ROOT/'docs/traceability/FULL_REQUIREMENTS_MATRIX.csv').open()))
    ids={r['id'] for r in requirements}; require(len(ids)==len(requirements),'Duplicate requirement IDs')
    counts=Counter(r['kind'] for r in requirements)
    require(counts=={'FR':94,'AT':63,'RT':63,'INVARIANT':10,'DERIVED':13},'Requirement inventory changed without review')
    cases=read('docs/testing/ACCEPTANCE_CASES.json')['cases']; case_ids={c['case_id'] for c in cases}
    ledger=list(csv.DictReader((ROOT/'docs/testing/TEST_LEDGER.csv').open()))
    require(len(case_ids)==len(cases) and case_ids=={r['case_id'] for r in ledger},'Case ledger mismatch')
    ledger_byid={r['case_id']:r for r in ledger}
    fixture_ids={r['fixture_id'] for name in ['MODULE_FIXTURES','CASE_FIXTURES'] for r in read('docs/testing/fixtures/'+name+'.json')['recipes']}
    for c in cases:
        require(c['slice']==ledger_byid[c['case_id']]['gate'],'Contradictory case phase '+c['case_id'])
        require(set(c['requirement_ids']) <= ids,'Unknown case requirement')
        require(set(c['fixture_ids']) <= fixture_ids,'Unknown case fixture')
        require(c['status']=='NOT_RUN','Planning scenario falsely marked executed')
        for key in ['given','steps','assertions','negative_case','fault_case','evidence_required','planned_test_path']:
            require(bool(c.get(key)),'Missing test definition '+key)
    tasks=read('docs/implementation/WORK_PACKAGES.json')['tasks']; task_ids={t['id'] for t in tasks}; done=set()
    require(len(task_ids)==len(tasks),'Duplicate task ID')
    for task in tasks:
        require(set(task['depends_on'])<=done,'Task order is cyclic or skips a dependency')
        require(set(task['test_case_ids'])<=case_ids,'Unknown task case')
        require(set(task['related_requirement_ids'])<=ids,'Unknown task requirement')
        require(bool(task['owned_paths']) and bool(task['done_conditions']),'Undefined task boundary')
        done.add(task['id'])
    plans=read('docs/testing/REQUIREMENT_TEST_PLANS.json')['plans']
    require(len(plans)==len(ids) and {p['requirement_id'] for p in plans}==ids,'Missing or duplicate requirement test plan')
    for p in plans:
        require(p['fixture_id'] in fixture_ids,'Unregistered requirement fixture')
        require(set(p['shared_case_refs'])<=case_ids,'Unknown shared test reference')
        require(set(p['work_package_refs'])<=task_ids and p['final_gate_task'] in task_ids,'Unknown work package reference')
        require(p['final_gate_task'].startswith(p['full_acceptance_slice']),'Final requirement gate is in wrong phase')
        require((ROOT/p['source']).is_file(),'Missing requirement source')
        require(bool(p['operation']) and bool(p['assertions']) and p['status']=='NOT_RUN','Incomplete requirement test definition')
    validate_closure(tasks, plans, cases)
    for p in list((ROOT/'contracts').glob('*.schema.json'))+list((ROOT/'state/schemas').glob('*.schema.json')):
        Draft202012Validator.check_schema(json.loads(p.read_text()))
    Draft202012Validator(read('contracts/decision-policy.schema.json')).validate(read('examples/behavior/decision-policy.json'))
    boundary=Draft202012Validator(read('contracts/runtime-boundaries.schema.json'),format_checker=FORMATS)
    for example in ['runtime_context.valid.json','runtime_response.valid.json']:boundary.validate(read('examples/payloads/'+example))
    require(not boundary.is_valid(read('examples/payloads/runtime_context.invalid.json')),'Invalid boundary example was accepted')
    table=read('contracts/commitment-control-v2.json');validate_control(table)
    Draft202012Validator(read('contracts/commitment-control-v2.schema.json')).validate(table)
    with (ROOT/'docs/architecture/CONTROL_TRANSITIONS.csv').open() as f:
        require(list(csv.DictReader(f)) == table['transitions'],'Control CSV differs from canonical table')
    validate_commitment(read('examples/payloads/commitment_v2.valid.json'))
    require(not Draft202012Validator(read('contracts/commitment-v2.schema.json'),format_checker=FORMATS).is_valid(read('examples/payloads/commitment_v2.invalid.json')),'Invalid commitment was accepted')
    require(set(table['states'])==set(read('contracts/commitment-v2.schema.json')['properties']['state']['enum']),'V2 state vocabulary mismatch')
    validate_guard_registry(table, read('contracts/guard-registry.json'), read('contracts/runtime-boundaries.schema.json'))
    require(build()==(ROOT/'QUATI_CONSOLIDATED_SPEC_V8_EN.md').read_text(),'Stale consolidated specification')
    record_validator=Draft202012Validator(read('state/schemas/engineering-record.schema.json'),format_checker=FORMATS)
    for p in (ROOT/'memory').glob('*/*.json'):
        record=json.loads(p.read_text());record_validator.validate(record)
        require(set(record['requirement_ids'])<=ids,'Memory record has unknown requirement')
        for ref in record['evidence_refs']:require((ROOT/ref).is_file(),'Missing memory evidence '+ref)
    state=read('docs/implementation/implementation_state.json')
    Draft202012Validator(read('state/schemas/implementation-state.schema.json'),format_checker=FORMATS).validate(state)
    validate_seal_references(state)
    memory_index=read(state['memory_registry_ref'])
    for record in memory_index['records']:
        actual=read(record['path'])
        require(record['record_id']==actual['record_id'] and record['status']==actual['status'],'Stale memory index')
    for ref in state['active_work']['memory_refs']:require((ROOT/ref).is_file(),'Missing active memory reference')
    if state['work_mode']=='SPECIFICATION_ONLY':
        require(state['execution_authorized'] is False,'Specification-only mode cannot authorize runtime edits')
    else:
        require(state['execution_authorized'] is True,'Implementation mode requires explicit authorization in canonical state')
    print(json.dumps({'status':'PASS','tier':'L0','requirements':len(ids),'shared_cases':len(cases),'requirement_plans':len(plans),'work_packages':len(tasks),'fixture_recipes':len(fixture_ids),'runtime_qualified':False,'semantic_coverage_requires_review':True},sort_keys=True))


if __name__=='__main__':main()
