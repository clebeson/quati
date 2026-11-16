"""Trusted policy gate for capability invocation (M25-FR-03, K6).

Wraps the pure ``quati.domain.policy.evaluate`` with the trusted policy state. The policy
file and its audited registry are loaded through
``quati.behavior.trusted_config.load_trusted_policy`` on every decision (RFC-014 5.1);
any loader failure is an unavailable state and therefore ``DENY policy_unavailable``.
There is no permissive fallback.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from quati.behavior.trusted_config import load_trusted_policy
from quati.domain.policy import KERNEL_BASELINE_VERSION, EffectIntent, PolicyContext, PolicyDecision, PolicyState
from quati.domain.policy import evaluate

LOCAL_OWNER_ROLE = "OWNER"


class LocalPolicyGate:
    def __init__(self, policy_state_provider: Callable[[], PolicyState], *, clock, ids,
                 runtime_profile: str = "S00", deployment: str = "LOCAL") -> None:
        self.policy_state_provider = policy_state_provider
        self.clock = clock
        self.ids = ids
        self.runtime_profile = runtime_profile
        self.deployment = deployment
        self.calls = 0

    @classmethod
    def from_config_dir(cls, config_dir: Path, *, tenant_id: str, installation_uid: int, clock, ids,
                        runtime_profile: str = "S00") -> "LocalPolicyGate":
        """``<config_dir>/policy.json`` checked against the head of ``<config_dir>/policy.registry.json``."""
        config_dir = Path(config_dir)

        def provider() -> PolicyState:
            return load_trusted_policy(config_dir / "policy.json", config_dir / "policy.registry.json",
                                       tenant_id=tenant_id, installation_uid=installation_uid)
        return cls(provider, clock=clock, ids=ids, runtime_profile=runtime_profile)

    def _state(self) -> PolicyState:
        try:
            state = self.policy_state_provider()
        except Exception:  # noqa: BLE001 - K6: a raising loader is an unavailable policy
            return PolicyState.unavailable("loader_error")
        return state if isinstance(state, PolicyState) else PolicyState.unavailable("loader_error")

    def policy_version(self) -> str:
        state = self._state()
        return state.policy_version if state.available else KERNEL_BASELINE_VERSION

    def decide(self, context, intent: EffectIntent, runtime_profile: str | None = None) -> PolicyDecision:
        """The local single-user principal holds the OWNER tenant role; agents and services hold none."""
        self.calls += 1
        role = LOCAL_OWNER_ROLE if context.principal_kind == "HUMAN" else None
        policy_context = PolicyContext(context.tenant_id, context.actor_id, context.principal_kind, tenant_role=role)
        return evaluate(policy_context, intent, self._state(), now=self.clock(), decision_id=self.ids("decision"),
                        runtime_profile=runtime_profile or self.runtime_profile, deployment=self.deployment)


__all__ = ["LOCAL_OWNER_ROLE", "LocalPolicyGate"]
