"""M25-FR-03 (S00 leg, plus the S02 narrowed-scope leg of the pure gate), L1 integration.

The trusted policy is a real 0600 ``policy.json`` whose version is the head of an audited
``policy.registry.json`` (built with the T02 adopt_policy/save_policy_registry API), loaded
through ``quati.behavior.trusted_config.load_trusted_policy``; the capability is a fixture handler whose
calls are recorded. No model and no network are involved.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import replace
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY_ROOT / "tests" / "unit"))

from s00_t03_support import TENANT, build, policy_document  # noqa: E402

from quati.adapters.fts_index import Fts5CapabilityIndex  # noqa: E402
from quati.adapters.policy_gate import LocalPolicyGate  # noqa: E402
from quati.application.discovery import DiscoveryService  # noqa: E402
from quati.behavior.trusted_config import load_policy, read_policy_snapshot, save_policy_registry  # noqa: E402
from quati.domain.policy import PolicyContext, PolicyRegistry, adopt_policy  # noqa: E402
from s00_t03_support import ACTOR  # noqa: E402

QUERY = "Find my next appointment"


def _config_dir(root: Path) -> Path:
    """policy.json (0600) plus registry revision 1 adopted by the HUMAN owner, as ``quati init`` does."""
    config = root / "config"
    config.mkdir(parents=True)
    path = config / "policy.json"
    path.write_bytes(json.dumps(policy_document()).encode())
    os.chmod(path, 0o600)
    observed = load_policy(read_policy_snapshot(path), tenant_id=TENANT, installation_uid=os.getuid(),
                           trusted_version=None)
    owner = PolicyContext(TENANT, ACTOR, "HUMAN", tenant_role="OWNER")
    registry = adopt_policy(PolicyRegistry.empty(TENANT), observed, expected_revision=0, actor=owner,
                            interactive=True, capability_context=False)
    save_policy_registry(config / "policy.registry.json", registry, expected_revision=0)
    return config


def _wired(root: Path, *, audit=None, profile: str = "S00", config: Path | None = None):
    harness = build(root)
    config = _config_dir(root) if config is None else config
    gate = LocalPolicyGate.from_config_dir(config, tenant_id=TENANT, installation_uid=os.getuid(),
                                           clock=harness.clock, ids=harness.ids, runtime_profile=profile)
    log: list[str] = []
    sink = audit or (lambda event: log.append(event["event"]))
    discovery = DiscoveryService(harness.registry, Fts5CapabilityIndex(), harness.handlers, policy_gate=gate,
                                 grants=harness.grants, clock=harness.clock, ids=harness.ids, audit=sink)
    original = harness.handlers.execute

    def recorded(handler, arguments, *, now):
        log.append("capability.call")
        return original(handler, arguments, now=now)

    harness.handlers.execute = recorded
    harness.install("calendar-read")
    return harness, gate, discovery, log


def _invoke(discovery, harness):
    turn = discovery.begin_turn(harness.operator)
    turn.search(turn.context, QUERY)
    return turn.invoke(turn.context, "fixtures.calendar-read", {"limit": 1}, "idem-fr03")


def test_verdict_audit_precedes_call_and_scope_is_narrowed(tmp_path: Path) -> None:
    audited: list[dict] = []
    harness, gate, discovery, log = _wired(tmp_path / "s00", audit=lambda event: (
        audited.append(event), None)[1])
    original = harness.handlers.execute
    harness.handlers.execute = lambda handler, arguments, *, now: (audited.append({"event": "capability.call"}),
                                                                  original(handler, arguments, now=now))[1]
    result = _invoke(discovery, harness)
    assert (result.status, result.trace["policy_verdict"], result.trace["handler_executed"]) == (
        "SUCCEEDED", "ALLOW", True)
    names = [event["event"] for event in audited]
    assert names.index("policy.decided") < names.index("capability.call")
    decided = [event for event in audited if event["event"] == "policy.decided"][0]
    assert decided["decision"]["verdict"] == "ALLOW" and decided["decision"]["reason_code"] == "read-own-spaces"
    scope = decided["decision"]["narrowed_scope"]
    assert scope["effect_id"] == decided["effect_id"] and scope["capability_id"] == "fixtures.calendar-read"
    # S02 leg: the same gate returns one narrowed scope per effect_id.
    _h2, gate_s02, discovery_s02, _log2 = _wired(tmp_path / "s02", profile="S02")
    turn = discovery_s02.begin_turn(_h2.operator)
    turn.search(turn.context, QUERY)
    first = turn.invoke(turn.context, "fixtures.calendar-read", {"limit": 1}, "k1")
    second = turn.invoke(turn.context, "fixtures.calendar-read", {"limit": 2}, "k2")
    assert first.trace["narrowed_scope"]["effect_id"] != second.trace["narrowed_scope"]["effect_id"]
    assert gate_s02.calls == 2


def test_fr03_fault_audit_failure_and_missing_scope_refuse_dispatch(tmp_path: Path) -> None:
    def failing(event):
        if event["event"] == "policy.decided":
            raise OSError("audit store down")

    harness, _gate, discovery, log = _wired(tmp_path / "a", audit=failing)
    result = _invoke(discovery, harness)
    assert (result.status, result.reason, result.trace["handler_executed"]) == (
        "UNAVAILABLE", "audit_unavailable", False)
    assert harness.handlers.total_invocations() == 0
    harness, gate, discovery, log = _wired(tmp_path / "b")
    real = gate.decide
    gate.decide = lambda ctx, intent, runtime_profile=None: replace(real(ctx, intent), narrowed_scope=None)
    result = _invoke(discovery, harness)
    assert (result.status, result.reason) == ("DENIED", "narrowed_scope_missing")
    harness, gate, discovery, log = _wired(tmp_path / "c")
    real = gate.decide

    def other_destination(ctx, intent, runtime_profile=None):
        decision = real(ctx, intent)
        return replace(decision, narrowed_scope={**decision.narrowed_scope, "destination_ref": "email:external"})

    gate.decide = other_destination
    result = _invoke(discovery, harness)
    assert (result.status, result.reason) == ("DENIED", "narrowed_scope_violation")
    assert "capability.call" not in log


def test_fr03_fault_unavailable_policy_file_denies_without_fallback(tmp_path: Path) -> None:
    legs = {}
    for leg in ("missing", "mode", "out_of_band", "invalid", "registry_missing", "registry_mode"):
        root = tmp_path / leg
        root.mkdir()
        config = _config_dir(root)
        path = config / "policy.json"
        if leg == "missing":
            path.unlink()
        elif leg == "mode":
            os.chmod(path, 0o644)
        elif leg == "out_of_band":
            document = policy_document()
            document["description"] = "edited outside Quati"
            path.write_bytes(json.dumps(document).encode())
        elif leg == "invalid":
            path.write_bytes(b"{not json")
        elif leg == "registry_missing":
            (config / "policy.registry.json").unlink()
        else:
            os.chmod(config / "policy.registry.json", 0o644)
        harness, gate, discovery, log = _wired(root, config=config)
        result = _invoke(discovery, harness)
        legs[leg] = (result.status, result.reason, result.trace["policy_verdict"], result.trace["handler_executed"])
        assert harness.handlers.total_invocations() == 0 and "capability.call" not in log
        assert "policy.decided" in log
    assert set(legs.values()) == {("DENIED", "policy_unavailable", "DENY", False)}
