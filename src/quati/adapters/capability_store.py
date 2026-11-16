"""Local file store for the capability registry (M14 persistence).

Layout under ``<state_dir>/capabilities/``: ``packages/<id>/<version>/`` immutable package
copies, ``registry.json`` (compare-and-swap ``revision``, temp + fsync + rename),
``capabilities.lock`` (lock_version 1) and ``audit.jsonl`` (append + fsync).

Everything under the root is owner-only (directories 0700, files 0600). The audit log is opened
without following a symlink and must be a private regular file; otherwise the append is refused
with the typed reason ``audit_unavailable`` and nothing is written (K7, M26). Tamper-evident
chaining of the log is S02 ledger work, not provided here.
"""

from __future__ import annotations

import copy
import fcntl
import json
import os
import shutil
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterable, Iterator

from quati.adapters.private_fs import open_private, private_directory, read_private, write_private
from quati.behavior.fsutil import atomic_write
from quati.behavior.manifest import PackageEntry, package_sha256, scan_package_dir
from quati.domain.canonical import canonical_bytes
from quati.domain.capability_registry import Refusal

STORE_SCHEMA = "quati-capability-store/1"
SECTIONS = ("records", "definitions", "bindings", "approvals", "history")


def default_registry_root() -> Path:
    base = os.environ.get("QUATI_DATA_DIR") or str(Path.home() / ".quati")
    return Path(base) / "capabilities"


def empty_state() -> dict:
    return {"schema": STORE_SCHEMA, "revision": 0, **{name: [] for name in SECTIONS}}


def _audit_unavailable() -> Refusal:
    return Refusal("UNAVAILABLE", "TEMPORARILY_UNAVAILABLE", "audit_unavailable",
                   "The audit log is not a private regular file; nothing was read or recorded.")


class FileRegistryStore:
    def __init__(self, root: Path, *, hook: Callable[[str], None] | None = None) -> None:
        self.root = Path(root)
        self.hook = hook
        self._lock_depth = 0

    # ------------------------------------------------------------------ registry.json
    @property
    def registry_path(self) -> Path:
        return self.root / "registry.json"

    def load(self) -> dict:
        if not self.registry_path.exists():
            return empty_state()
        return json.loads(self.registry_path.read_bytes())

    @contextmanager
    def _locked(self) -> Iterator[None]:
        """Exclusive cross-process store lock; re-entrant inside one store instance."""
        if self._lock_depth:
            self._lock_depth += 1
            try:
                yield
            finally:
                self._lock_depth -= 1
            return
        self._private_root()
        with os.fdopen(open_private(self.root / "registry.flock", os.O_RDWR, tighten=True), "a+b") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            self._lock_depth = 1
            try:
                yield
            finally:
                self._lock_depth = 0
                fcntl.flock(handle, fcntl.LOCK_UN)

    def _private_root(self) -> None:
        """The state directory (when this user owns it) and the registry root are owner-only."""
        parent = self.root.parent
        if parent.is_dir() and not parent.is_symlink() and parent.stat().st_uid == os.getuid():
            private_directory(parent)
        private_directory(self.root)

    def transaction(self) -> Iterator[None]:
        """Hold the store lock across a whole load -> stage -> CAS commit -> publish sequence."""
        return self._locked()

    def commit(self, state: dict, *, expected_revision: int) -> dict:
        """Write ``state`` as revision ``expected_revision + 1`` unless another writer won."""
        with self._locked():
            if self.load()["revision"] != expected_revision:
                raise Refusal("CONFLICT", "REVISION_CONFLICT", "REVISION_CONFLICT", "registry store changed")
            written = copy.deepcopy(state)
            written["revision"] = expected_revision + 1
            atomic_write(self.registry_path, json.dumps(written, sort_keys=True, indent=1).encode() + b"\n",
                         hook=self.hook, point="registry")
        return written

    # ------------------------------------------------------------------ packages
    def package_dir(self, capability_id: str, version: str) -> Path:
        return self.root / "packages" / capability_id / version

    def store_package(self, capability_id: str, version: str, entries: Iterable[PackageEntry]) -> str:
        """Stage and publish in one locked step (kept for callers outside the install transaction)."""
        with self._locked():
            sha, staging = self.stage_package(entries)
            self.publish_package(capability_id, version, staging)
        return sha

    def stage_package(self, entries: Iterable[PackageEntry]) -> tuple[str, Path]:
        """Write a content-addressed staging copy (``staging/<sha256>``); nothing is published yet."""
        entries = tuple(entries)
        sha = package_sha256(entries)
        self._private_root()
        staging = self.root / "staging" / sha
        shutil.rmtree(staging, ignore_errors=True)
        private_directory(staging)
        for entry in entries:
            target = staging / entry.path
            private_directory(target.parent)
            write_private(target, entry.data)
        return sha, staging

    def publish_package(self, capability_id: str, version: str, staging: Path) -> None:
        """Rename a staged package into place; called only after the registry CAS committed."""
        final = self.package_dir(capability_id, version)
        private_directory(final.parent)
        shutil.rmtree(final, ignore_errors=True)        # an orphan or a tampered copy of the committed digest
        os.replace(staging, final)

    def discard_staging(self, staging: Path) -> None:
        shutil.rmtree(staging, ignore_errors=True)

    def read_package(self, capability_id: str, version: str) -> tuple[str, dict[str, bytes]] | None:
        """``(sha256, {path: bytes})`` from one scan of the stored package; ``None`` when unreadable."""
        try:
            entries = scan_package_dir(self.package_dir(capability_id, version))
        except Exception:  # noqa: BLE001 - an unreadable stored package is a digest mismatch
            return None
        return package_sha256(entries), {entry.path: entry.data for entry in entries}

    def package_digest(self, capability_id: str, version: str) -> str | None:
        try:
            return package_sha256(scan_package_dir(self.package_dir(capability_id, version)))
        except Exception:  # noqa: BLE001 - an unreadable stored package is a digest mismatch
            return None

    # ------------------------------------------------------------------ lock file
    @property
    def lock_path(self) -> Path:
        return self.root / "capabilities.lock"

    def lock_entries(self) -> list[dict]:
        if not self.lock_path.exists():
            return []
        return json.loads(self.lock_path.read_bytes())["entries"]

    def write_lock_entry(self, entry: dict) -> None:
        """Read-modify-write of ``capabilities.lock`` under the store lock."""
        with self._locked():
            self._write_lock_entry(entry)

    def _write_lock_entry(self, entry: dict) -> None:
        entries = [item for item in self.lock_entries()
                   if (item["id"], item["version"]) != (entry["id"], entry["version"])]
        entries.append(entry)
        entries.sort(key=lambda item: (item["id"], item["version"]))
        atomic_write(self.lock_path, canonical_bytes({"lock_version": 1, "entries": entries}) + b"\n",
                     hook=self.hook, point="lock")

    # ------------------------------------------------------------------ audit
    @property
    def audit_path(self) -> Path:
        return self.root / "audit.jsonl"

    def append_audit(self, event: dict) -> None:
        """Append one event to the private audit log, or refuse with ``audit_unavailable`` (fail closed)."""
        line = canonical_bytes(event) + b"\n"
        try:
            self._private_root()
            descriptor = open_private(self.audit_path, os.O_WRONLY | os.O_APPEND)
            with os.fdopen(descriptor, "ab") as handle:
                handle.write(line)
                handle.flush()
                os.fsync(handle.fileno())
        except OSError:
            raise _audit_unavailable() from None

    def audit_events(self) -> list[dict]:
        """Events of the private audit log; a symlinked or insecure log is ``audit_unavailable``, never read."""
        try:
            raw = read_private(self.audit_path)
        except OSError:
            raise _audit_unavailable() from None
        return [json.loads(line) for line in (raw or b"").splitlines() if line]


__all__ = ["FileRegistryStore", "STORE_SCHEMA", "default_registry_root", "empty_state"]
