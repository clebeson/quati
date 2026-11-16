"""Trusted configuration loaders: LOCAL tenant policy file (RFC-014 section 5.1), the
policy registry of audited versions, and the decision-policy sidecar.

Every policy-file failure yields an unavailable ``PolicyState`` (K6 fail closed) whose
``cause`` is kept for ``quati doctor``; nothing here raises on a bad policy file.
"""

from __future__ import annotations

import errno
import json
import os
from pathlib import Path
import stat

from quati.behavior.contracts import ContractCatalog, default_catalog, parse_json, schema_violation
from quati.behavior.fsutil import CrashHook, atomic_write, locked
from quati.domain.canonical import canonical_bytes
from quati.domain.decision_policy import DecisionPolicy, check_decision_policy
from quati.domain.diagnostics import ContractViolation, ErrorCode, violation
from quati.domain.policy import PolicyFileSnapshot, PolicyRegistry, PolicyState

POLICY_SCHEMA = "policy.schema.json"
DECISION_POLICY_SCHEMA = "decision-policy.schema.json"
MAX_POLICY_BYTES = 1024 * 1024
REQUIRED_MODE = 0o600

__all__ = ["PolicyFileSnapshot", "read_policy_snapshot", "load_policy", "load_policy_registry",
           "save_policy_registry", "load_trusted_policy", "load_decision_policy"]


def read_policy_snapshot(path: Path) -> PolicyFileSnapshot:
    """Read the policy file without following symlinks; at most MAX_POLICY_BYTES + 1 bytes."""
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return PolicyFileSnapshot(None, None, None, "missing")
    except OSError as exc:
        cause = "not_regular_file" if exc.errno == errno.ELOOP else "unreadable"
        return PolicyFileSnapshot(None, None, None, cause)
    status = os.fstat(descriptor)
    if not stat.S_ISREG(status.st_mode):
        os.close(descriptor)
        return PolicyFileSnapshot(None, None, None, "not_regular_file")
    with os.fdopen(descriptor, "rb") as handle:
        content = handle.read(MAX_POLICY_BYTES + 1)
    return PolicyFileSnapshot(content, status.st_mode & 0o7777, status.st_uid)


def load_policy(snapshot: PolicyFileSnapshot, *, tenant_id: str, installation_uid: int,
                trusted_version: str | None, catalog: ContractCatalog | None = None) -> PolicyState:
    """Owner, mode, parse, schema, tenant, then the out-of-band check; any failure is K6."""
    if snapshot.read_error is not None or snapshot.content is None:
        return PolicyState.unavailable(snapshot.read_error or "missing")
    if snapshot.owner_uid != installation_uid:
        return PolicyState.unavailable("wrong_owner")
    if snapshot.mode != REQUIRED_MODE:
        return PolicyState.unavailable("wrong_mode")
    try:
        try:
            document = parse_json(snapshot.content, max_bytes=MAX_POLICY_BYTES)
        except ContractViolation:
            return PolicyState.unavailable("parse_error")
        if (catalog or default_catalog()).errors(document, POLICY_SCHEMA):
            return PolicyState.unavailable("schema_invalid")
        return PolicyState.from_document(document, tenant_id=tenant_id, trusted_version=trusted_version)
    except Exception:  # noqa: BLE001 - any loader fault fails closed (K6)
        return PolicyState.unavailable("loader_error")


def _protected_file_error(snapshot: PolicyFileSnapshot, installation_uid: int) -> str | None:
    if snapshot.read_error is not None:
        return snapshot.read_error
    if snapshot.owner_uid != installation_uid:
        return "wrong_owner"
    if snapshot.mode != REQUIRED_MODE:
        return "wrong_mode"
    return None


def load_policy_registry(path: Path, *, tenant_id: str, installation_uid: int | None = None) -> PolicyRegistry:
    """Load the registry with the policy-file protections: no symlink, regular file, owner, 0600.

    Trust boundary (LOCAL profile): these checks stop other users and symlink swaps; a
    same-UID process can rewrite both files, so tamper evidence against it is out of scope.
    """
    snapshot = read_policy_snapshot(Path(path))
    if snapshot.read_error == "missing":
        return PolicyRegistry.empty(tenant_id)
    cause = _protected_file_error(snapshot, os.getuid() if installation_uid is None else installation_uid)
    if cause is not None:
        raise violation(ErrorCode.CONFIG_INVALID, cause, "$", "policy registry file is not protected")
    try:
        document = parse_json(snapshot.content, max_bytes=MAX_POLICY_BYTES)
    except ContractViolation as exc:
        raise violation(ErrorCode.CONFIG_INVALID, exc.reason, "$", "policy registry is unreadable") from None
    registry = PolicyRegistry.from_json(document)
    if registry.tenant_id != tenant_id:
        raise violation(ErrorCode.CONFIG_INVALID, "wrong_tenant", "tenant_id", "registry belongs to another tenant")
    return registry


def save_policy_registry(path: Path, registry: PolicyRegistry, *, expected_revision: int,
                         hook: CrashHook | None = None) -> None:
    """Compare-and-swap on the stored revision, then an atomic replace (mode 0600).

    The read-compare-replace runs under an exclusive lock on ``<path>.lock``.
    """
    path = Path(path)
    with locked(path):
        current = load_policy_registry(path, tenant_id=registry.tenant_id)
        if current.revision != expected_revision:
            raise violation(ErrorCode.REVISION_CONFLICT, "REVISION_CONFLICT", "revision", "stale registry revision")
        atomic_write(path, canonical_bytes(registry.to_json()), hook=hook, point="policy.write_registry")


def load_trusted_policy(policy_path: Path, registry_path: Path, *, tenant_id: str, installation_uid: int,
                        catalog: ContractCatalog | None = None) -> PolicyState:
    """Registry then policy file; a registry that fails its checks makes policy unavailable (K6)."""
    try:
        registry = load_policy_registry(registry_path, tenant_id=tenant_id, installation_uid=installation_uid)
    except ContractViolation as exc:
        return PolicyState.unavailable(f"registry_{exc.reason}")
    return load_policy(read_policy_snapshot(Path(policy_path)), tenant_id=tenant_id,
                       installation_uid=installation_uid, trusted_version=registry.active_version,
                       catalog=catalog)


def load_decision_policy(raw: bytes, *, catalog: ContractCatalog | None = None) -> DecisionPolicy:
    """Parse strictly, validate the schema, then the loader-only rules; failures are CONFIG_INVALID."""
    try:
        document = parse_json(raw)
    except ContractViolation as exc:
        raise violation(ErrorCode.CONFIG_INVALID, exc.reason, exc.path, "decision policy is not valid JSON") from None
    errors = (catalog or default_catalog()).errors(document, DECISION_POLICY_SCHEMA)
    if errors:
        raise schema_violation(errors, code=ErrorCode.CONFIG_INVALID, rule_class=None)
    return check_decision_policy(json.loads(canonical_bytes(document)))
