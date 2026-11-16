"""Shared deterministic setup for the S00-T03 registry and discovery tests (M14, M15, M25).

Everything is synthetic: a fixed clock, seeded identifiers, a temporary state
directory, the canonical local-default policy and the public fixture catalog.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from quati.adapters.capability_store import FileRegistryStore
from quati.adapters.fixture_capabilities import (
    FIXTURE_HANDLERS, FixtureHandlerRegistry, LOCAL_READ_GRANTS, StaticGrants, fixture_manifest,
    install_fixture, write_fixture_package, write_package)
from quati.adapters.fts_index import Fts5CapabilityIndex
from quati.adapters.policy_gate import LocalPolicyGate
from quati.application.capability_registry import RegistryService
from quati.application.discovery import DiscoveryService
from quati.application.identity import RequestContext, ScopeAuthorization
from quati.domain.policy import PolicyState, policy_version

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
TENANT = "01JD0000000000000000000000"
OTHER_TENANT = "01JD0000000000000000000001"
ACTOR = "01JD00000000000000000000AA"
AGENT = "01JD00000000000000000000AG"
PERSONAL = "01JD00000000000000000000P1"
ORGANIZATION = "01JD00000000000000000000O1"
START = datetime(2026, 11, 16, 12, 0, 0, tzinfo=timezone.utc)


class FakeClock:
    def __init__(self, start: datetime = START) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: int) -> None:
        self.now = self.now + timedelta(seconds=seconds)


class SeededIds:
    def __init__(self) -> None:
        self.count = 0

    def __call__(self, prefix: str) -> str:
        self.count += 1
        return f"{prefix}-{self.count:05d}"


def context(actor: str = ACTOR, tenant: str = TENANT, kind: str = "HUMAN", request: str = "request-0001",
            spaces: tuple[str, ...] = (PERSONAL, ORGANIZATION)) -> RequestContext:
    return RequestContext(actor_id=actor, tenant_id=tenant, space_ids=spaces, request_id=request,
                          trace_id="trace-0001", session_id="session-0001", token_jti="jti-000000000001",
                          authenticated_origin_ref="local-os:device-key",
                          deadline_at="2026-11-16T12:00:30+00:00", principal_kind=kind)


def policy_document(tenant: str = TENANT) -> dict:
    document = json.loads((REPOSITORY_ROOT / "examples/policies/local-default.policy.json").read_text())
    document["tenant_id"] = tenant
    return document


def trusted_policy_state(tenant: str = TENANT) -> PolicyState:
    document = policy_document(tenant)
    return PolicyState.from_document(document, tenant_id=tenant, trusted_version=policy_version(document))


class SyntheticDirectory:
    """Fix round 6 (audit F5) setup: ``DiscoveryService`` requires an AuthorizationPort. This is the
    harness directory for its synthetic contexts: both harness spaces granted, the OWNER tenant role,
    and every tenant's registry owned by the ORGANIZATION space. It stands in for the request-derived
    fallback the service used to build when no port was passed (same grants for the default context)."""

    def space_grants(self, context):
        return PERSONAL, ORGANIZATION

    def tenant_role(self, context):
        return "OWNER"

    def registry_space(self, tenant_id):
        return ORGANIZATION


@dataclass
class Harness:
    root: Path
    clock: FakeClock
    ids: SeededIds
    store: FileRegistryStore
    handlers: FixtureHandlerRegistry
    registry: RegistryService
    grants: StaticGrants
    gate: LocalPolicyGate
    discovery: DiscoveryService
    operator: RequestContext

    def restart(self) -> "Harness":
        """A new set of objects over the same state directory (process restart)."""
        return build(self.root, clock=self.clock, ids=self.ids, grants=self.grants.permissions,
                     policy_state=self.gate.policy_state_provider())

    def install(self, name: str, *, enable: bool = True, handler: str | None = "default"):
        return install_fixture(self.registry, self.operator, name, self.root / "sources",
                               enable_fixture=enable, fixture_handler=handler)

    def turn(self, ctx: RequestContext | None = None, features=None):
        return self.discovery.begin_turn(ctx or self.operator, model_features=features)


def build(root: Path, *, clock: FakeClock | None = None, ids: SeededIds | None = None,
          grants=LOCAL_READ_GRANTS, policy_state: PolicyState | None = None, audit=None,
          handlers: FixtureHandlerRegistry | None = None) -> Harness:
    clock = clock or FakeClock()
    ids = ids or SeededIds()
    store = FileRegistryStore(root / "state" / "capabilities")
    handlers = handlers or FixtureHandlerRegistry(FIXTURE_HANDLERS)
    registry = RegistryService(store, handlers, clock=clock, ids=ids)
    grant_port = StaticGrants(frozenset(grants))
    state = trusted_policy_state() if policy_state is None else policy_state
    gate = LocalPolicyGate(lambda: state, clock=clock, ids=ids, directory=SyntheticDirectory(),
                           runtime_profile="S00")      # fix round 7 (N17): the gate reads the role from the directory
    discovery = DiscoveryService(registry, Fts5CapabilityIndex(), handlers, policy_gate=gate, grants=grant_port,
                                 clock=clock, ids=ids, audit=audit,
                                 authorization=ScopeAuthorization(SyntheticDirectory(), clock))
    return Harness(root, clock, ids, store, handlers, registry, grant_port, gate, discovery, context())


def handler_for(capability_id: str, base: str = "forecast-lime", permissions: tuple[str, ...] | None = None):
    """A test-source fixture handler whose TRUSTED capability id is ``capability_id`` (same function,
    effect and, unless overridden, permission floor as ``base``)."""
    source = FIXTURE_HANDLERS[base]
    return replace(source, name=capability_id.split(".", 1)[1], default_capability_id=capability_id,
                   effect_class=source.trusted_effect,
                   required_permissions=source.trusted_permissions if permissions is None else permissions)


def handlers_with(*capability_ids: str, base: str = "forecast-lime",
                  permissions: tuple[str, ...] | None = None) -> FixtureHandlerRegistry:
    extra = {handler.name: handler for handler in (handler_for(cid, base, permissions) for cid in capability_ids)}
    return FixtureHandlerRegistry({**FIXTURE_HANDLERS, **extra})


def manifest_copy(name: str) -> dict:
    return copy.deepcopy(fixture_manifest(name))


__all__ = ["handler_for", "handlers_with", "ACTOR", "AGENT", "ORGANIZATION", "OTHER_TENANT", "PERSONAL", "START", "TENANT", "FakeClock",
           "Harness", "SeededIds", "SyntheticDirectory", "build", "context", "manifest_copy", "policy_document", "replace",
           "trusted_policy_state", "write_fixture_package", "write_package"]
