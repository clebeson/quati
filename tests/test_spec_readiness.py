"""L0 readiness integrity and discriminating negative checks; no runtime proof."""
import copy
import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'spec_tools'))
from validate_readiness import main,read,validate_control


def test_complete_planning_graph_has_no_dangling_ids_or_missing_plans():
    main()


def test_v2_rejects_delivery_without_authenticated_acknowledgement():
    table=read('contracts/commitment-control-v2.json')
    next(t for t in table['transitions'] if t['target']=='DELIVERED')['guard']='always'
    with pytest.raises(ValueError,match='acknowledgement'):
        validate_control(table)


def test_v2_rejects_missing_timeout_recovery():
    table=read('contracts/commitment-control-v2.json')
    table['transitions']=[t for t in table['transitions'] if not(t['source']=='WAITING_INPUT' and t['event']=='deadline')]
    with pytest.raises(ValueError,match='deadline'):
        validate_control(table)


def test_v2_cannot_cancel_unknown_effect_as_if_absent():
    table=read('contracts/commitment-control-v2.json')
    next(t for t in table['transitions'] if t['source']=='CANCEL_REQUESTED' and t['target']=='CANCELLED')['guard']='any_effect_unknown'
    with pytest.raises(ValueError,match='cancellation'):
        validate_control(table)


def test_requirement_cannot_be_orphaned_from_final_task():
    from validate_readiness import validate_closure
    tasks=read('docs/implementation/WORK_PACKAGES.json')['tasks']
    plans=read('docs/testing/REQUIREMENT_TEST_PLANS.json')['plans']
    cases=read('docs/testing/ACCEPTANCE_CASES.json')['cases']
    owner=next(t for t in tasks if t['id']==plans[0]['test_owner_task'])
    owner['owned_requirement_plan_ids'].remove(plans[0]['plan_id'])
    with pytest.raises(ValueError,match='ownership'):
        validate_closure(tasks,plans,cases)


def test_pass_gate_requires_exact_seal_record():
    from validate_readiness import validate_seal_references
    state=read('docs/implementation/implementation_state.json')
    # Independent of the live gate status: a PASS gate whose seal references are removed must be rejected.
    state['slices']['S00']['gates']['S00-GATE-01']='PASS'
    state['slices']['S00']['gate_seal_refs']['S00-GATE-01']=[]
    with pytest.raises(ValueError,match='seal'):
        validate_seal_references(state)


def test_v2_nonterminal_requires_next_action():
    from validate_readiness import validate_commitment
    from jsonschema import ValidationError
    with pytest.raises(ValidationError):
        validate_commitment(read('examples/payloads/commitment_v2.invalid.json'))


@pytest.mark.parametrize('mutation',['evidence','source','missing_digest','escape'])
def test_seal_rejects_changed_or_unbound_provenance(tmp_path, mutation):
    import hashlib, json
    from validate_readiness import validate_seal_provenance
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    source=tmp_path/'source.txt';source.write_text('source')
    evidence=tmp_path/'evidence.txt';evidence.write_text('observed')
    manifest=tmp_path/'snapshot.json'
    manifest.write_text(json.dumps({'schema_version':'quati-source-snapshot/1','files':{'source.txt':digest(source)}}))
    seal={'artifact_sha256':{'source.txt':digest(source)},'evidence_refs':['evidence.txt'],
          'evidence_sha256':{'evidence.txt':digest(evidence)},
          'source_snapshot':{'manifest_path':'snapshot.json','manifest_sha256':digest(manifest)}}
    validate_seal_provenance(seal,tmp_path)
    if mutation=='evidence':evidence.write_text('changed')
    if mutation=='source':source.write_text('changed')
    if mutation=='missing_digest':seal['evidence_sha256']={}
    if mutation=='escape':seal['source_snapshot']['manifest_path']='../outside'
    with pytest.raises(ValueError):validate_seal_provenance(seal,tmp_path)


@pytest.mark.parametrize('mutation', [None, 'evidence', 'unbound_transcript'])
def test_commit_seal_binds_test_log_and_transcript(tmp_path, mutation):
    import hashlib
    from validate_readiness import validate_seal_provenance
    log = tmp_path / 'test.log'
    transcript = tmp_path / 'transcript.txt'
    log.write_text('command: offline check; exit: 0')
    transcript.write_text('redacted reviewer session')
    seal = {
        'evidence_refs': ['test.log', 'transcript.txt'],
        'evidence_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in (log, transcript)},
        'commit_evidence': {'commit_sha': 'a' * 40, 'test_log_ref': 'test.log',
                            'transcript_ref': 'transcript.txt'},
    }
    if mutation == 'evidence':
        log.write_text('fabricated completion')
    if mutation == 'unbound_transcript':
        seal['commit_evidence']['transcript_ref'] = 'unbound.txt'
    if mutation:
        with pytest.raises(ValueError):
            validate_seal_provenance(seal, tmp_path)
    else:
        validate_seal_provenance(seal, tmp_path)


def test_decision_policy_cannot_remove_blocking_authority_or_accept_unknown_keys():
    from jsonschema import Draft202012Validator
    schema = Draft202012Validator(read('contracts/decision-policy.schema.json'))
    policy = read('examples/behavior/decision-policy.json')
    schema.validate(policy)
    policy['behavior_policy']['blocking_fields'].remove('authorization_scope')
    assert not schema.is_valid(policy)
    policy = read('examples/behavior/decision-policy.json')
    policy['behavior_policy']['disable_authorization'] = True
    assert not schema.is_valid(policy)


@pytest.mark.parametrize('mutation', [None, 'missing_test_seal', 'wrong_commit', 'wrong_scope'])
def test_slice_acceptance_requires_three_same_source_seals(tmp_path, monkeypatch, mutation):
    import hashlib
    import json
    import validate_readiness as checker
    (tmp_path / 'test.log').write_text('observed test output')
    (tmp_path / 'transcript.txt').write_text('redacted independent review')
    evidence = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in tmp_path.iterdir()}
    state = read('docs/implementation/implementation_state.json')
    state['slices'] = {'S00': state['slices']['S00']}
    item = state['slices']['S00']
    item.update(status='PASS', commit='a' * 40)
    item['gates'] = {'S00-GATE-01': 'PASS'}
    refs = []
    index = {'records': []}
    for kind in ('TESTS_VERIFIED', 'EVIDENCE_VERIFIED', 'SLICE_ACCEPTED'):
        if mutation == 'missing_test_seal' and kind == 'TESTS_VERIFIED':
            continue
        seal = dict(seal_id=kind, kind=kind, scope_ids=['S00'], verdict='PASS',
                    issued_at='2026-11-15T00:00:00Z',
                    issuer={'identity': 'synthetic-reviewer', 'role': 'reviewer',
                            'independent_of_authors': True},
                    requirement_ids=[], test_ids=[], evidence_refs=list(evidence),
                    evidence_sha256=evidence, proof_tiers=['L0'], rationale='Synthetic contract example',
                    unresolved_findings=[], supersedes=None, signature=None,
                    commit_evidence={'commit_sha': 'b' * 40 if mutation == 'wrong_commit' else 'a' * 40,
                                     'test_log_ref': 'test.log', 'transcript_ref': 'transcript.txt'})
        path = tmp_path / (kind + '.json')
        path.write_text(json.dumps(seal))
        ref = dict(seal_id=kind, path=path.name, record_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                   kind=kind, scope_id='S01' if mutation == 'wrong_scope' else 'S00')
        refs.append(ref)
        index['records'].append(ref)
    item['gate_seal_refs'] = {'S00-GATE-01': refs}
    original_provenance = checker.validate_seal_provenance
    monkeypatch.setattr(checker, 'ROOT', tmp_path)
    monkeypatch.setattr(checker, 'read', lambda path: index if path == state['seal_registry_ref'] else json.loads((ROOT / path).read_text()))
    monkeypatch.setattr(checker, 'validate_seal_provenance',
                        lambda seal: original_provenance(seal, tmp_path))
    if mutation:
        with pytest.raises(ValueError):
            checker.validate_seal_references(state)
    else:
        checker.validate_seal_references(state)
