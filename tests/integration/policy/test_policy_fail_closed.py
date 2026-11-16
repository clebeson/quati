"""M25-RT-01 oracle locator (docs/prds/M25.md, Test oracles), policy-gate legs.

``test_every_broken_policy_state_denies_all_effects`` runs the POL-04 legs from
``tests/unit/test_policy_load.py`` (absent, invalid JSON, schema-invalid, other tenant,
mode 0644, other owner, out-of-band edit, loader raising) against real temp files.
The registry legs below add the file-level protections of the policy registry.
The ``quati doctor --json`` and ``policy apply --adopt`` CLI legs are outside S00-T02.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "unit"))

from s00_t02_support import TENANT, base_policy  # noqa: E402
from test_policy_load import OWNER, UID, decide, trusted_registry  # noqa: E402
from test_policy_load import test_pol_04 as test_every_broken_policy_state_denies_all_effects  # noqa: E402,F401
from quati.behavior.trusted_config import load_trusted_policy, save_policy_registry  # noqa: E402


def test_registry_file_failures_deny_every_effect(tmp_path: Path) -> None:
    policy = tmp_path / "policy.json"
    policy.write_text(json.dumps(base_policy()))
    os.chmod(policy, 0o600)
    registry_path = tmp_path / "state" / "policy-registry.json"
    save_policy_registry(registry_path, trusted_registry(base_policy()), expected_revision=0)
    assert load_trusted_policy(policy, registry_path, tenant_id=TENANT, installation_uid=UID).available
    link = tmp_path / "link.json"
    link.symlink_to(registry_path)
    legs = {
        "registry_wrong_mode": (registry_path, 0o644, UID),
        "registry_wrong_owner": (registry_path, 0o600, UID + 1),
        "registry_not_regular_file": (link, 0o600, UID),
    }
    for cause, (path, mode, installation_uid) in legs.items():
        os.chmod(registry_path, mode)
        state = load_trusted_policy(policy, path, tenant_id=TENANT, installation_uid=installation_uid)
        assert (state.available, state.cause) == (False, cause)
        for effect in ("read", "write", "dangerous"):
            decision = decide(state, effect)
            assert (decision.verdict, decision.reason_code) == ("DENY", "policy_unavailable"), (cause, effect)
    registry_path.write_bytes(b"{broken")
    os.chmod(registry_path, 0o600)
    state = load_trusted_policy(policy, registry_path, tenant_id=TENANT, installation_uid=UID)
    assert (state.available, state.cause) == (False, "registry_PARSE_ERROR")
    assert OWNER.tenant_id == TENANT
