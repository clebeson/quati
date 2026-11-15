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
    state['slices']['S00']['gates']['S00-GATE-01']='PASS'
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
    manifest.write_text(json.dumps({'schema_version':'secma-source-snapshot/1','files':{'source.txt':digest(source)}}))
    seal={'artifact_sha256':{'source.txt':digest(source)},'evidence_refs':['evidence.txt'],
          'evidence_sha256':{'evidence.txt':digest(evidence)},
          'source_snapshot':{'manifest_path':'snapshot.json','manifest_sha256':digest(manifest)}}
    validate_seal_provenance(seal,tmp_path)
    if mutation=='evidence':evidence.write_text('changed')
    if mutation=='source':source.write_text('changed')
    if mutation=='missing_digest':seal['evidence_sha256']={}
    if mutation=='escape':seal['source_snapshot']['manifest_path']='../outside'
    with pytest.raises(ValueError):validate_seal_provenance(seal,tmp_path)
