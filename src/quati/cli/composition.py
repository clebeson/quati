"""Composition root for the S00-T04 ask runtime and the operator capability commands.

Wires the file registry, the in-source fixture handlers, the local trusted policy gate, the
FTS5 index and the compiled behavior prompt for one authenticated RequestContext. Clock,
identifiers and the handler registry are injectable so tests stay deterministic.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import quati
from quati.adapters.capability_store import FileRegistryStore, default_registry_root
from quati.adapters.fixture_capabilities import (
    FIXTURE_HANDLERS, FIXTURE_NAMES, LOCAL_READ_GRANTS, FixtureHandlerRegistry, StaticGrants, write_fixture_package)
from quati.adapters.fts_index import Fts5CapabilityIndex
from quati.adapters.policy_gate import LocalPolicyGate
from quati.application.ask import AskRuntime
from quati.application.capability_commands import CapabilityCommands
from quati.application.capability_registry import RegistryService
from quati.application.discovery import DiscoveryService
from quati.behavior.compiler import BehaviorCompiler
from quati.domain.policy import TrustedPolicy

REPOSITORY_ROOT = Path(quati.__file__).resolve().parents[2]
BEHAVIOR_PROFILE = "examples/behavior/executive-secretary.yaml"
MODEL_ROLE_REF = "cheap_tool_capable"


def system_clock() -> datetime:
    return datetime.now(timezone.utc)


def random_ids(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def _parts(identity, context, *, clock, ids, handlers):
    handlers = handlers or FixtureHandlerRegistry(FIXTURE_HANDLERS)
    store = FileRegistryStore(default_registry_root())
    registry = RegistryService(store, handlers, clock=clock, ids=ids)
    gate = LocalPolicyGate.from_config_dir(identity.directory, tenant_id=context.tenant_id,
                                           installation_uid=os.getuid(), clock=clock, ids=ids)
    discovery = DiscoveryService(registry, Fts5CapabilityIndex(), handlers, policy_gate=gate,
                                 grants=StaticGrants(LOCAL_READ_GRANTS), clock=clock, ids=ids)
    return registry, gate, discovery


def ask_runtime(identity, context, *, clock=system_clock, ids=random_ids, handlers=None) -> AskRuntime:
    registry, gate, discovery = _parts(identity, context, clock=clock, ids=ids, handlers=handlers)
    prompt = BehaviorCompiler(REPOSITORY_ROOT).compile(
        BEHAVIOR_PROFILE, trusted_policy=TrustedPolicy("default", gate.policy_version()), model_role_ref=MODEL_ROLE_REF)
    return AskRuntime(discovery=discovery, registry=registry, prompt=prompt)


def capability_commands(identity, evidence_sink, *, clock=system_clock, ids=random_ids,
                        handlers=None) -> CapabilityCommands:
    context = identity.authenticate()
    registry, _gate, discovery = _parts(identity, context, clock=clock, ids=ids, handlers=handlers)
    sources = default_registry_root().parent / "fixture_sources"
    return CapabilityCommands(context=context, registry=registry, discovery=discovery, evidence_sink=evidence_sink,
                              write_fixture_package=lambda name: write_fixture_package(sources, name),
                              fixture_names=FIXTURE_NAMES)


__all__ = ["BEHAVIOR_PROFILE", "MODEL_ROLE_REF", "ask_runtime", "capability_commands", "random_ids", "system_clock"]
