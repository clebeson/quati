"""L0 regressions for independently reproduced CT findings; not runtime proof."""
import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'spec_tools'))
from behavior_compiler import load_yaml, validate_behavior, validate_machine, validate_schema


def profile():
    return load_yaml(ROOT / 'examples/behavior/executive-secretary.yaml')


def test_ct02_invalid_embedded_capability_schema_rejected():
    capability = json.loads((ROOT / 'examples/capabilities/example_analytic_research.json').read_text())
    capability['input_schema'] = {'type': 'not-a-type'}
    with pytest.raises(ValueError):
        validate_schema(capability, 'scs-capability.schema.json')


def test_ct02_remote_schema_reference_rejected():
    capability = json.loads((ROOT / 'examples/capabilities/example_analytic_research.json').read_text())
    capability['input_schema'] = {'$ref': 'https://untrusted.invalid/schema'}
    with pytest.raises(ValueError):
        validate_schema(capability, 'scs-capability.schema.json')


def test_ct03_protected_delivery_bypass_rejected():
    machine = load_yaml(ROOT / 'examples/statecharts/commitment.yaml')
    machine['transitions'].append({'source': 'RECEIVED', 'event': 'bypass', 'target': 'DELIVERED', 'guard': 'always', 'action': 'record_delivery'})
    with pytest.raises(ValueError, match='Protected'):
        validate_machine(machine)


def test_ct03_guard_replacement_rejected():
    machine = load_yaml(ROOT / 'examples/statecharts/commitment.yaml')
    machine['transitions'][0]['guard'] = 'always'
    with pytest.raises(ValueError, match='Protected'):
        validate_machine(machine)


@pytest.mark.parametrize(('section', 'field', 'value'), [
    ('interaction', 'clarification_style', 'only_blocking'),
    ('execution', 'max_investigation_loops', 1),
    ('execution', 'safe_read_ahead', False),
    ('models', 'specialist_role', 'another_approved_role'),
    ('context', 'max_capability_candidates', 3),
])
def test_ct04_effective_options_change_prompt(section, field, value):
    document = profile()
    before, _ = validate_behavior(document)
    document[section][field] = value
    after, _ = validate_behavior(document)
    assert before['prompt_hash'] != after['prompt_hash']


def test_ct04_profile_cannot_exceed_machine_loop_limit():
    document = profile()
    document['execution']['max_investigation_loops'] = 9
    with pytest.raises(ValueError, match='budget'):
        validate_behavior(document)


def test_ct05_language_override_requires_language():
    document = profile()
    document['interaction']['language_policy'] = 'explicit_override'
    with pytest.raises(ValueError):
        validate_behavior(document)


def test_ct06_receipt_includes_trusted_inputs():
    receipt, _ = validate_behavior(profile())
    assert receipt['compiler_version']
    assert len(receipt['policy_hash']) == 64
    assert receipt['source_versions']['statechart'] == '1.0.0'
    validate_schema(receipt, 'prompt-build-receipt.schema.json')


def test_ct07_duplicate_yaml_keys_rejected(tmp_path):
    path = tmp_path / 'duplicate.yaml'
    path.write_text('policy_ref: trusted_policy/default\npolicy_ref: untrusted\n')
    with pytest.raises(ValueError, match='Duplicate'):
        load_yaml(path)


def test_ct08_invalid_timestamp_rejected():
    document = {key: 'x' for key in ['provider_id', 'document_id', 'version', 'tenant_id', 'title', 'content_ref', 'source_uri', 'acl_ref']}
    document.update(visibility='private', retrieved_at='not-a-time')
    with pytest.raises(ValueError):
        validate_schema(document, 'brain-document.schema.json')


def test_ct01_reference_states_fit_commitment_contract():
    machine = load_yaml(ROOT / 'examples/statecharts/commitment.yaml')
    schema = json.loads((ROOT / 'contracts/commitment.schema.json').read_text())
    assert set(machine['states']) == set(schema['properties']['state']['enum'])


def test_ct03_cross_product_guard_action_bypass_rejected():
    machine = load_yaml(ROOT / 'examples/statecharts/commitment.yaml')
    machine['transitions'][0].update(guard='under_budget', action='merge_context')
    with pytest.raises(ValueError, match='Protected'):
        validate_machine(machine)


def test_ct03_delivery_action_cannot_be_retargeted():
    machine = load_yaml(ROOT / 'examples/statecharts/commitment.yaml')
    machine['transitions'][0]['action'] = 'record_delivery'
    with pytest.raises(ValueError, match='Protected'):
        validate_machine(machine)
