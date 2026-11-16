"""POL-04 (contribution, full owner S00-T05) and M25-RT-01 legs at the policy gate.

Every broken or untrusted policy state denies every effect with ``policy_unavailable``
(K6); only an explicit HUMAN interactive adoption trusts a valid out-of-band file.
The ``quati doctor`` and ``quati policy apply --adopt`` CLI wiring is outside S00-T02.
"""

from __future__ import annotations

import dataclasses
import json
import os
from pathlib import Path

import pytest

from s00_t02_support import ACTOR, NOW, OTHER_TENANT, TENANT, CounterIds, base_policy
from quati.behavior.contracts import ContractCatalog
from quati.behavior.trusted_config import (
    load_policy,
    load_policy_registry,
    read_policy_snapshot,
    save_policy_registry,
)
from quati.domain.canonical import digest
from quati.domain.diagnostics import ContractViolation, ErrorCode
from quati.domain.policy import (
    EffectIntent,
    KERNEL_BASELINE_VERSION,
    PolicyContext,
    PolicyFileSnapshot,
    PolicyRegistry,
    adopt_policy,
    evaluate,
    policy_version,
)

UID = os.getuid()
OWNER = PolicyContext(tenant_id=TENANT, actor_id=ACTOR, principal_kind="HUMAN", tenant_role="OWNER")


def intent(effect: str, **overrides) -> EffectIntent:
    fields = dict(effect_id="eff-1", actor_id=ACTOR, tenant_id=TENANT, capability_id="research.fixture",
                  capability_version="1.0.0", binding_id="bind-1", binding_version="1", operation="invoke",
                  destination_ref="fixture:local", policy_version="0" * 64, idempotency_key="idem-1",
                  input_digest="1" * 64, effect_class=effect, data_class="PUBLIC_SYNTHETIC",
                  integrity="TRUSTED", steering_args_user_confirmed=True, space_kind="PERSONAL")
    fields.update(overrides)
    return EffectIntent(**fields)


def decide(state, effect: str, profile: str = "S02"):
    return evaluate(OWNER, intent(effect), state, now=NOW, decision_id=CounterIds()(), runtime_profile=profile)


def write_policy(path: Path, document, mode: int = 0o600) -> Path:
    path.write_bytes(document if isinstance(document, bytes) else json.dumps(document).encode())
    os.chmod(path, mode)
    return path


def trusted_registry(document) -> PolicyRegistry:
    """A registry whose active version is the given document (as if adopted earlier)."""
    registry = PolicyRegistry.empty(TENANT)
    snapshot = PolicyFileSnapshot(content=json.dumps(document).encode(), mode=0o600, owner_uid=UID)
    state = load_policy(snapshot, tenant_id=TENANT, installation_uid=UID, trusted_version=None)
    return adopt_policy(registry, state, expected_revision=0, actor=OWNER, interactive=True,
                        capability_context=False)


class RaisingCatalog(ContractCatalog):
    def errors(self, document, schema_name):
        raise RuntimeError("loader exploded")


def test_pol_04(tmp_path: Path) -> None:
    good = base_policy()
    registry = trusted_registry(good)
    trusted = registry.active_version
    assert trusted == policy_version(good)
    path = tmp_path / "policy.json"

    unknown_field = base_policy()
    unknown_field["rules"][0]["priority"] = 100
    out_of_band = base_policy()
    out_of_band["rules"].append({"rule_id": "deny-fixture-reads", "verdict": "DENY",
                                 "match": {"capability_id": "research.*", "effects": ["read"]}})
    legs = {
        "missing": (None, 0o600, UID, "missing"),
        "invalid_json": (b"{not json", 0o600, UID, "parse_error"),
        "schema_invalid": ({"policy_schema_version": "1"}, 0o600, UID, "schema_invalid"),
        "unknown_rule_field": (unknown_field, 0o600, UID, "schema_invalid"),
        "wrong_tenant": (dict(good, tenant_id=OTHER_TENANT), 0o600, UID, "wrong_tenant"),
        "mode_0644": (good, 0o644, UID, "wrong_mode"),
        "other_owner": (good, 0o600, UID + 1, "wrong_owner"),
        "out_of_band": (out_of_band, 0o600, UID, "out_of_band_change"),
    }
    for leg, (document, mode, installation_uid, cause) in legs.items():
        if path.exists():
            path.unlink()
        if document is not None:
            write_policy(path, document, mode)
        state = load_policy(read_policy_snapshot(path), tenant_id=TENANT, installation_uid=installation_uid,
                            trusted_version=trusted)
        assert (state.available, state.cause) == (False, cause), leg
        for effect in ("read", "write", "dangerous"):
            for profile in ("S00", "S02"):
                decision = decide(state, effect, profile)
                assert (decision.verdict, decision.reason_code) == ("DENY", "policy_unavailable"), (leg, effect)
                assert decision.policy_version == KERNEL_BASELINE_VERSION
                assert decision.matched_rule_ids == () and decision.narrowed_scope is None

    # Loader exception leg.
    write_policy(path, good)
    state = load_policy(read_policy_snapshot(path), tenant_id=TENANT, installation_uid=UID,
                        trusted_version=trusted, catalog=RaisingCatalog())
    assert (state.available, state.cause) == (False, "loader_error")

    # Valid trusted file: reads are allowed, S00 still denies writes (K3).
    state = load_policy(read_policy_snapshot(path), tenant_id=TENANT, installation_uid=UID,
                        trusted_version=trusted)
    assert state.available and state.policy_version == trusted
    assert decide(state, "read", "S00").verdict == "ALLOW"
    assert decide(state, "write", "S00").reason_code == "s00_no_effects"

    # Only an explicit adoption activates a valid out-of-band file.
    write_policy(path, out_of_band)
    state = load_policy(read_policy_snapshot(path), tenant_id=TENANT, installation_uid=UID,
                        trusted_version=registry.active_version)
    assert state.cause == "out_of_band_change" and state.observed_version == policy_version(out_of_band)
    for refused in (dict(interactive=False), dict(capability_context=True),
                    dict(actor=dataclasses.replace(OWNER, principal_kind="AGENT")),
                    dict(expected_revision=0)):
        kwargs = dict(expected_revision=1, actor=OWNER, interactive=True, capability_context=False)
        kwargs.update(refused)
        with pytest.raises(ContractViolation) as caught:
            adopt_policy(registry, state, **kwargs)
        assert caught.value.code in {ErrorCode.FORBIDDEN, ErrorCode.REVISION_CONFLICT}
    adopted = adopt_policy(registry, state, expected_revision=1, actor=OWNER, interactive=True,
                           capability_context=False)
    assert adopted.revision == 2 and adopted.active_version == policy_version(out_of_band)
    assert registry.active_version == trusted  # immutable: the old registry value is unchanged
    assert [v.policy_version for v in adopted.versions] == [trusted, policy_version(out_of_band)]
    state = load_policy(read_policy_snapshot(path), tenant_id=TENANT, installation_uid=UID,
                        trusted_version=adopted.active_version)
    assert state.available
    assert (decide(state, "read").verdict, decide(state, "read").reason_code) == ("DENY", "deny-fixture-reads")
    assert decide(state, "write", "S00").reason_code == "s00_no_effects"  # K3 cannot be disabled
    assert decide(state, "dangerous", "S02").verdict == "APPROVAL_REQUIRED"  # K2 cannot be disabled

    # Fault: corrupt the file while running; the next decision fails closed.
    path.write_bytes(b'{"policy_schema_version": "1", "tenant_id": ')
    state = load_policy(read_policy_snapshot(path), tenant_id=TENANT, installation_uid=UID,
                        trusted_version=adopted.active_version)
    assert decide(state, "read").reason_code == "policy_unavailable"


def test_policy_snapshot_reader_never_follows_symlinks_or_specials(tmp_path: Path) -> None:
    real = write_policy(tmp_path / "real.json", base_policy())
    link = tmp_path / "policy.json"
    link.symlink_to(real)
    snapshot = read_policy_snapshot(link)
    assert snapshot.content is None and snapshot.read_error == "not_regular_file"
    state = load_policy(snapshot, tenant_id=TENANT, installation_uid=UID, trusted_version=None)
    assert state.cause == "not_regular_file"
    directory = tmp_path / "dir.json"
    directory.mkdir()
    assert read_policy_snapshot(directory).read_error == "not_regular_file"
    big = tmp_path / "big.json"
    big.write_bytes(b" " * (1024 * 1024 + 1))
    os.chmod(big, 0o600)
    state = load_policy(read_policy_snapshot(big), tenant_id=TENANT, installation_uid=UID, trusted_version=None)
    assert state.cause == "parse_error"
    unreadable = PolicyFileSnapshot(content=None, mode=0o600, owner_uid=UID, read_error="unreadable")
    assert load_policy(unreadable, tenant_id=TENANT, installation_uid=UID, trusted_version=None).cause == "unreadable"


def test_policy_without_trusted_version_is_untrusted(tmp_path: Path) -> None:
    path = write_policy(tmp_path / "policy.json", base_policy())
    state = load_policy(read_policy_snapshot(path), tenant_id=TENANT, installation_uid=UID, trusted_version=None)
    assert (state.available, state.cause) == (False, "out_of_band_change")


def test_policy_registry_round_trip_and_cas(tmp_path: Path) -> None:
    registry = trusted_registry(base_policy())
    path = tmp_path / "state" / "policy-registry.json"
    save_policy_registry(path, registry, expected_revision=0)
    loaded = load_policy_registry(path, tenant_id=TENANT)
    assert loaded == registry
    with pytest.raises(ContractViolation) as caught:
        save_policy_registry(path, registry, expected_revision=0)
    assert caught.value.code is ErrorCode.REVISION_CONFLICT
    assert load_policy_registry(tmp_path / "absent.json", tenant_id=TENANT) == PolicyRegistry.empty(TENANT)
    with pytest.raises(ContractViolation) as caught:
        load_policy_registry(path, tenant_id=OTHER_TENANT)
    assert caught.value.reason == "wrong_tenant"
    path.write_text('{"tenant_id": 5}')
    with pytest.raises(ContractViolation) as caught:
        load_policy_registry(path, tenant_id=TENANT)
    assert caught.value.code is ErrorCode.CONFIG_INVALID
    # A registry whose recorded history was edited is detected.
    document = registry.to_json()
    document["versions"][0]["policy_version"] = "f" * 64
    path.write_text(json.dumps(document))
    with pytest.raises(ContractViolation) as caught:
        load_policy_registry(path, tenant_id=TENANT)
    assert caught.value.reason == "registry_inconsistent"
    assert digest(registry.to_json()) == digest(PolicyRegistry.from_json(registry.to_json()).to_json())


def test_adopt_requires_a_valid_document_for_the_tenant() -> None:
    registry = PolicyRegistry.empty(TENANT)
    for content, cause in ((b"{", "parse_error"),
                           (json.dumps(dict(base_policy(), tenant_id=OTHER_TENANT)).encode(), "wrong_tenant")):
        state = load_policy(PolicyFileSnapshot(content=content, mode=0o600, owner_uid=UID), tenant_id=TENANT,
                            installation_uid=UID, trusted_version=None)
        assert state.cause == cause
        with pytest.raises(ContractViolation) as caught:
            adopt_policy(registry, state, expected_revision=0, actor=OWNER, interactive=True,
                         capability_context=False)
        assert (caught.value.code, caught.value.reason) == (ErrorCode.FORBIDDEN, "policy_not_adoptable")
    state = load_policy(PolicyFileSnapshot(content=json.dumps(base_policy()).encode(), mode=0o600,
                                           owner_uid=UID), tenant_id=TENANT, installation_uid=UID,
                        trusted_version=None)
    with pytest.raises(ContractViolation) as caught:
        adopt_policy(registry, state, expected_revision=0,
                     actor=dataclasses.replace(OWNER, tenant_id=OTHER_TENANT), interactive=True,
                     capability_context=False)
    assert caught.value.reason == "wrong_tenant"
