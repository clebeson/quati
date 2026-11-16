"""L1 RFC-013 identity contributions using real signatures and private local files."""
from dataclasses import replace
from pathlib import Path
import json
import os

import pytest

from quati.application.identity import AccessDenied, authorize_read, verify_token
from quati.adapters.local_identity import LocalIdentity


def test_local_owner_initialization_and_verified_context(tmp_path):
    identity = LocalIdentity(tmp_path / 'config')
    assert not identity.diagnostics()['initialized']
    result = identity.initialize()
    assert result['secret_store'] == 'owner_only_file'
    context = identity.authenticate()
    assert context.principal_kind == 'HUMAN'
    assert context.profile == 'LOCAL'
    assert context.actor_id != context.tenant_id
    assert len(context.space_ids) == 2
    assert identity.initialize()['tenant_id'] == result['tenant_id']
    assert identity.directory.stat().st_mode & 0o777 == 0o700
    for path in identity.directory.iterdir():
        assert path.stat().st_mode & 0o777 == 0o600
    assert 'private_key' not in json.dumps(result)


def test_missing_local_credentials_fail_before_business_lookup(tmp_path):
    identity = LocalIdentity(tmp_path / 'missing')
    with pytest.raises(AccessDenied, match='UNAUTHENTICATED'):
        identity.authenticate()
    assert not identity.directory.exists()


@pytest.mark.parametrize('mutation', ['missing_key', 'key_permissions', 'config_permissions', 'config_changed', 'wrong_owner'])
def test_damaged_identity_never_silently_reinitializes(tmp_path, monkeypatch, mutation):
    identity = LocalIdentity(tmp_path / 'config')
    identity.initialize()
    if mutation == 'missing_key':
        identity.key_path.unlink()
    elif mutation == 'key_permissions':
        identity.key_path.chmod(0o644)
    elif mutation == 'config_permissions':
        identity.record_path.chmod(0o666)
    elif mutation == 'config_changed':
        record = json.loads(identity.record_path.read_text())
        record['tenant_id'] = '00000000000000000000000000'
        identity.record_path.write_text(json.dumps(record))
    else:
        monkeypatch.setattr(os, 'getuid', lambda: os.stat(identity.record_path).st_uid + 1)
    with pytest.raises(AccessDenied):
        identity.authenticate()


def test_identity_rejects_symlinked_config(tmp_path):
    real = tmp_path / 'real'
    real.mkdir()
    link = tmp_path / 'link'
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(AccessDenied):
        LocalIdentity(link).initialize()
    assert list(real.iterdir()) == []


def test_capability_process_cannot_initialize_owner(tmp_path, monkeypatch):
    monkeypatch.setenv('QUATI_CAPABILITY_CONTEXT', '1')
    with pytest.raises(AccessDenied):
        LocalIdentity(tmp_path / 'config').initialize()
    assert not (tmp_path / 'config').exists()


def test_out_of_scope_and_wrong_tenant_reads_rejected_at_n_one(tmp_path):
    identity = LocalIdentity(tmp_path / 'config')
    identity.initialize()
    context = identity.authenticate()
    assert authorize_read(context, context.tenant_id, context.space_ids[0])
    for tenant, space in [(context.tenant_id, 'other-space'), ('other-tenant', context.space_ids[0])]:
        with pytest.raises(AccessDenied, match='FORBIDDEN'):
            authorize_read(context, tenant, space)


@pytest.mark.parametrize('mutation', ['identity', 'expiry', 'audience', 'signature'])
def test_typed_tokens_reject_forgery_and_expiry(tmp_path, mutation):
    identity = LocalIdentity(tmp_path / 'config')
    identity.initialize()
    token, public_key = identity.issue_token()
    claims = dict(token.claims)
    if mutation == 'identity':
        claims['sub'] = '00000000000000000000000000'
        token = replace(token, claims=claims)
    elif mutation == 'expiry':
        # A valid signature is still insufficient after expiry.
        with pytest.raises(AccessDenied):
            verify_token(token, public_key, now=claims['exp'] + 61)
        return
    elif mutation == 'audience':
        with pytest.raises(AccessDenied):
            verify_token(token, public_key, audience='other-resource')
        return
    else:
        token = replace(token, signature=b'not-a-valid-signature')
    with pytest.raises(AccessDenied):
        verify_token(token, public_key)
