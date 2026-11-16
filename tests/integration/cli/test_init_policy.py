"""RFC-014 section 5.1 / M25-RT-01 / M01 DoctorReport.policy through the public CLI.

Proof tier: L1 public process. ``quati init`` installs the LOCAL default policy with the tenant
filled in and records its ``policy_version`` as registry revision 1 with a ``policy.changed``
audit receipt; ``quati doctor --json`` reports the trusted-loader verdict as a cause code only.
Every run is a ``python -m quati`` subprocess in temporary directories with every ``QUATI_*``
variable removed; no provider, network or model is involved.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = REPOSITORY_ROOT / 'examples' / 'policies' / 'local-default.policy.json'


def quati_json(value) -> bytes:
    """Independent quati-json/1 oracle (BOUNDARY_CONTRACTS.md Canonical digest)."""
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def run(root: Path, *argv: str):
    env = {key: value for key, value in os.environ.items() if not key.startswith('QUATI_')}
    env['PYTHONPATH'] = os.pathsep.join(filter(None, [str(REPOSITORY_ROOT / 'src'),
                                                   os.environ.get('QUATI_TEST_COVERAGE_BOOTSTRAP')]))
    env['QUATI_CONFIG_DIR'] = str(root / 'config')
    env['QUATI_DATA_DIR'] = str(root / 'data')
    completed = subprocess.run([sys.executable, '-m', 'quati', *argv], cwd=REPOSITORY_ROOT, env=env,
                               capture_output=True, check=False)
    return completed.returncode, json.loads(completed.stdout)


def doctor_policy(root: Path):
    code, value = run(root, 'doctor', '--json')
    assert code == 0 and value['status'] == 'SUCCEEDED'
    return value['data']['policy']


def snapshot(config: Path) -> dict[str, tuple[bytes, int]]:
    return {path.name: (path.read_bytes(), path.stat().st_mode & 0o7777) for path in sorted(config.iterdir())}


@pytest.fixture
def initialized(tmp_path: Path):
    code, value = run(tmp_path, 'init', '--json')
    assert code == 0 and value['status'] == 'SUCCEEDED'
    return tmp_path, value


def test_fresh_init_installs_trusted_policy_registry_and_audit_event(initialized):
    root, value = initialized
    config, data = root / 'config', value['data']
    policy_path, registry_path = config / 'policy.json', config / 'policy.registry.json'
    for path in (policy_path, registry_path):
        info = path.lstat()
        assert info.st_mode & 0o7777 == 0o600 and info.st_uid == os.getuid() and not path.is_symlink()
    document = json.loads(policy_path.read_bytes())
    expected = {**json.loads(TEMPLATE.read_bytes()), 'tenant_id': data['tenant_id']}
    assert document == expected
    version = hashlib.sha256(quati_json(document)).hexdigest()
    registry = json.loads(registry_path.read_bytes())
    assert registry['tenant_id'] == data['tenant_id'] and registry['revision'] == 1
    (record,) = registry['versions']
    assert (record['revision'], record['policy_version'], record['actor_id'], record['previous']) == (
        1, version, data['principal_id'], None)
    assert data['policy'] == {'action': 'INSTALLED', 'reason': None, 'policy_version': version,
                              'registry_revision': 1}
    (reference,) = value['evidence_refs']
    _, digest, path = reference.split(':', 2)
    raw = Path(path).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest and Path(path).parent == root / 'data' / 'receipts'
    event = json.loads(raw)
    assert {key: event[key] for key in ('kind', 'event_type', 'source', 'tenant_id', 'actor_id',
                                         'old_policy_version', 'new_policy_version', 'registry_revision',
                                         'diff_digest')} == {
        'kind': 'audit_event', 'event_type': 'policy.changed', 'source': 'init', 'tenant_id': data['tenant_id'],
        'actor_id': data['principal_id'], 'old_policy_version': None, 'new_policy_version': version,
        'registry_revision': 1, 'diff_digest': hashlib.sha256(policy_path.read_bytes()).hexdigest()}
    assert b'read-own-spaces' not in raw  # the audit event carries digests, not policy content
    assert doctor_policy(root) == {'status': 'AVAILABLE', 'reason': None}


def test_hand_edited_policy_is_out_of_band(initialized):
    root, _ = initialized
    path = root / 'config' / 'policy.json'
    document = json.loads(path.read_bytes())
    document['description'] = 'Hand edited, still schema valid.'
    path.write_bytes(json.dumps(document).encode())
    assert path.stat().st_mode & 0o7777 == 0o600
    assert doctor_policy(root) == {'status': 'UNAVAILABLE', 'reason': 'out_of_band_change'}


def test_registry_wrong_mode_or_deleted_or_forged_is_unavailable(initialized):
    root, _ = initialized
    registry = root / 'config' / 'policy.registry.json'
    original = registry.read_bytes()
    registry.chmod(0o644)
    assert doctor_policy(root) == {'status': 'UNAVAILABLE', 'reason': 'registry_wrong_mode'}
    registry.chmod(0o600)
    assert doctor_policy(root) == {'status': 'AVAILABLE', 'reason': None}
    forged = json.loads(original)
    forged['versions'][0]['policy_version'] = '0' * 64
    registry.write_bytes(json.dumps(forged).encode())
    policy = doctor_policy(root)
    assert policy['status'] == 'UNAVAILABLE' and policy['reason'].startswith('registry_')
    registry.unlink()
    assert doctor_policy(root) == {'status': 'UNAVAILABLE', 'reason': 'out_of_band_change'}


def test_init_twice_leaves_policy_and_registry_unchanged(initialized):
    root, first = initialized
    before = snapshot(root / 'config')
    receipts = sorted((root / 'data' / 'receipts').iterdir())
    code, second = run(root, 'init', '--json')
    assert code == 0 and second['status'] == 'SUCCEEDED'
    assert second['data']['policy'] == {'action': 'UNCHANGED', 'reason': 'policy_exists'}
    assert second['evidence_refs'] == []
    assert (second['data']['tenant_id'], second['data']['principal_id']) == (
        first['data']['tenant_id'], first['data']['principal_id'])
    assert snapshot(root / 'config') == before
    assert sorted((root / 'data' / 'receipts').iterdir()) == receipts


def test_init_never_replaces_a_hand_edited_policy_or_a_lone_registry(initialized):
    root, _ = initialized
    config = root / 'config'
    policy = config / 'policy.json'
    policy.write_bytes(b'{"hand": "edit"}')
    before = snapshot(config)
    assert run(root, 'init', '--json')[1]['data']['policy'] == {'action': 'UNCHANGED', 'reason': 'policy_exists'}
    assert snapshot(config) == before
    policy.unlink()
    before = snapshot(config)
    assert run(root, 'init', '--json')[1]['data']['policy'] == {'action': 'UNCHANGED',
                                                                 'reason': 'registry_exists'}
    assert snapshot(config) == before and not policy.exists()
    assert doctor_policy(root) == {'status': 'UNAVAILABLE', 'reason': 'missing'}
