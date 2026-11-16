"""LOCAL policy file and audited registry (RFC-014 section 5.1): composition-root helpers.

``install`` is called by ``quati init``: it validates the default policy with the tenant filled
in, writes ``<config_dir>/policy.json`` atomically (0600) and records its ``policy_version`` as
registry revision 1 in ``<config_dir>/policy.registry.json``. It never replaces an existing
policy or registry file. ``state`` is the trusted-loader verdict used by ``quati doctor``.
"""
import hashlib
import json
import os
from pathlib import Path

from quati.behavior.contracts import ASSET_ROOT
from quati.behavior.fsutil import atomic_write, locked
from quati.behavior.trusted_config import load_policy, load_trusted_policy, read_policy_snapshot, save_policy_registry
from quati.domain.canonical import canonical_bytes
from quati.domain.policy import PolicyFileSnapshot, PolicyRegistry, PolicyState, PolicyVersionRecord

TEMPLATE = ASSET_ROOT / 'examples' / 'policies' / 'local-default.policy.json'
POLICY_FILE = 'policy.json'
REGISTRY_FILE = 'policy.registry.json'


def state(config_dir, tenant_id):
    """M25-RT-01: registry and policy checks; the cause code is the only detail returned."""
    policy_path = Path(config_dir) / POLICY_FILE
    if tenant_id is None:
        return PolicyState.unavailable(read_policy_snapshot(policy_path).read_error or 'identity_unavailable')
    return load_trusted_policy(policy_path, Path(config_dir) / REGISTRY_FILE, tenant_id=tenant_id,
                               installation_uid=os.getuid())


def install(config_dir, tenant_id, principal_id):
    """Return the outcome for the init Response; an installed policy also returns its audit event."""
    policy_path, registry_path = Path(config_dir) / POLICY_FILE, Path(config_dir) / REGISTRY_FILE
    with locked(policy_path):
        for path, reason in ((policy_path, 'policy_exists'), (registry_path, 'registry_exists')):
            if os.path.lexists(path):
                return {'action': 'UNCHANGED', 'reason': reason}, None
        try:
            document = json.loads(TEMPLATE.read_bytes())
        except OSError:
            return {'action': 'NOT_INSTALLED', 'reason': 'template_missing'}, None
        raw = canonical_bytes({**document, 'tenant_id': tenant_id})
        verdict = load_policy(PolicyFileSnapshot(raw, 0o600, os.getuid()), tenant_id=tenant_id,
                              installation_uid=os.getuid(), trusted_version=None)
        if verdict.cause != 'out_of_band_change':  # validated in memory; only "not yet audited" may remain
            return {'action': 'NOT_INSTALLED', 'reason': verdict.cause}, None
        version = verdict.observed_version
        atomic_write(policy_path, raw, point='policy.init_write_policy')
        record = PolicyVersionRecord.seal(1, version, principal_id, None)
        save_policy_registry(registry_path, PolicyRegistry(tenant_id, 1, (record,)), expected_revision=0)
    event = {'kind': 'audit_event', 'event_type': 'policy.changed', 'source': 'init', 'tenant_id': tenant_id,
             'actor_id': principal_id, 'old_policy_version': None, 'new_policy_version': version,
             'registry_revision': 1, 'diff_digest': hashlib.sha256(raw).hexdigest()}
    return {'action': 'INSTALLED', 'reason': None, 'policy_version': version, 'registry_revision': 1}, event
