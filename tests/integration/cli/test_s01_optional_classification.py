"""S01-T01: optional classifier fields remain optional on the public CLI boundary."""
import hashlib
import json

import pytest

from test_s01_conversation import WORK, classified, command, final, workspace


@pytest.mark.parametrize('confidence', [None, 0.5])
def test_absent_model_reference_is_not_invented_by_public_projection(workspace, capsys, confidence):
    """L2 scripted provider: preserve optional presence while suppressing free model strings."""
    _, active = workspace
    proposal = {key: value for key, value in WORK.items() if key not in ('commitment_ref', 'confidence')}
    if confidence is not None:
        proposal['confidence'] = confidence
    proposal['reason_code'] = 'Untrusted model text must remain undisplayed'
    active.add(classified(proposal), final(), final(), final())
    code, values, _ = command(capsys, 'ask', '--json', '--', 'Inspect this synthetic request')
    assert code == 4 and len(values) == 1
    data = values[0]['data']
    assert data['classification'] == proposal | {'reason_code': 'CLASSIFICATION_VALIDATED'}
    assert 'commitment_ref' not in data['classification']
    assert ('confidence' in data['classification']) == (confidence is not None)
    assert data['classification_stage'] == 'SCHEMA_VALIDATED'
    assert data['classification_sha256'] == hashlib.sha256(json.dumps(
        proposal, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()
    assert proposal['reason_code'] not in json.dumps(values[0])
    assert data['tool_calls'] == [] and data['launched'] is False and data['delivered'] is False
