"""These are L0 reference compiler tests, NOT runtime or LLM conformance tests."""
import copy,json,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'spec_tools'))
from behavior_compiler import load_yaml,validate_machine,validate_behavior,validate_schema,render_mermaid

def machine():return load_yaml(ROOT/'examples/statecharts/commitment.yaml')
def profile():return load_yaml(ROOT/'examples/behavior/executive-secretary.yaml')

def test_valid_statechart():
    assert validate_machine(machine())['transition_count']>=10

def test_statechart_renders_mermaid():
    assert 'stateDiagram-v2' in render_mermaid(machine())

def test_machine_unreachable_state_rejected():
    m=machine();m['states'].append('UNREACHABLE');
    with pytest.raises(ValueError,match='Unreachable'):validate_machine(m)

def test_machine_unknown_guard_rejected():
    m=machine();m['transitions'][0]['guard']='execute_python';
    with pytest.raises(ValueError,match='Unregistered guard'):validate_machine(m)

def test_machine_unknown_action_rejected():
    m=machine();m['transitions'][0]['action']='send_money';
    with pytest.raises(ValueError,match='Unregistered action'):validate_machine(m)

def test_duplicate_transition_rejected():
    m=machine();m['transitions'].append(copy.deepcopy(m['transitions'][0]));
    with pytest.raises(ValueError,match='Ambiguous transition'):validate_machine(m)

def test_behavior_determinism():
    a,_=validate_behavior(profile());b,_=validate_behavior(profile());assert a==b

def test_profile_change_updates_hash():
    p=profile();a,_=validate_behavior(p);p['interaction']['verbosity']='balanced';b,_=validate_behavior(p)
    assert a['prompt_hash']!=b['prompt_hash']

def test_unapproved_policy_ref_rejected():
    p=profile();p['policy_ref']='untrusted/disable_checks';
    with pytest.raises(ValueError,match='Unapproved policy'):validate_behavior(p)

def test_malicious_template_is_rejected_by_schema():
    p=profile();p['exec_python']='os.system("whoami")';
    with pytest.raises(ValueError,match='Schema error'):validate_behavior(p)

def test_scs_write_requires_approval():
    c=json.loads((ROOT/'examples/capabilities/example_analytic_research.json').read_text())
    c['effects']='dangerous';c['requires_approval']=False
    with pytest.raises(ValueError):validate_schema(c,'scs-capability.schema.json')

def test_scs_draft_cannot_be_enabled():
    c=json.loads((ROOT/'examples/capabilities/example_analytic_research.json').read_text())
    c['lifecycle']='enabled';c['assurance']='DRAFT'
    with pytest.raises(ValueError):validate_schema(c,'scs-capability.schema.json')

def test_state_machine_terminal_has_no_outgoing():
    m=machine();m['transitions'].append({'source':'DELIVERED','event':'falsify','target':'IN_PROGRESS','guard':'always','action':'record_progress'})
    with pytest.raises(ValueError,match='Terminal states'):validate_machine(m)

def test_missing_statechart_rejected():
    p=profile();p['statechart_ref']='missing/flow.yaml'
    with pytest.raises(ValueError,match='Statechart must resolve'):validate_behavior(p)
