"""Local file store for the capability registry (M14 persistence).

Layout under ``<state_dir>/capabilities/``: ``packages/<id>/<version>/`` immutable package
copies, ``registry.json`` (compare-and-swap ``revision``, temp + fsync + rename),
``capabilities.lock`` (lock_version 1) and ``audit.jsonl`` (append + fsync).

Everything under the root is owner-only (directories 0700, files 0600). Every operation first
verifies the directory chain (the state directory, then the registry root: real directories of
the current user, never a symlink) through ``private_fs.state_directory``, before any read, lock,
write or audit append; an unsafe chain raises ``UnsafeStatePath`` and nothing is touched. A read
creates nothing: an absent root is an empty registry. Every file is read and opened through the
private-file helpers (no-follow, non-blocking, regular, single link, owner, mode).

Verification order (docs/prds/M01.md, Data directory rules 1 and 2). ``prepare`` runs before the
command's authorization decision is logged: the directory chain, ``packages`` and ``staging``, and the
fixed store files by their metadata only (nothing below the registry is opened or listed for a
principal that may still be denied; M02 authorization order row 7). ``verify_packages`` verifies
every directory and file of the stored and staged packages; a store instance runs it once, before
its first registry read or lock, which the use cases reach only after an allowed decision.

Commit ordering (rule 3): ``stage_package`` does everything that can fail for a storage reason -
the staging copy and the creation and verification of the publish location - and the registry
service calls it before the compare-and-swap commit and its audit events. A step that can only
follow the commit (the rename into place, the lock entry, the audit events of the committed change)
raises ``StoreChangeIncomplete`` when it fails, never an error that says nothing was changed. The
store recognises a committed change by the write-ahead protocol of the registry service: a
``registry.intent`` event appended through this store instance, then the commit.

The audit log is opened without following a symlink and must be a private regular file whose
every line is one JSON object; otherwise reads and appends alike are refused with the typed
reason ``audit_unavailable`` and nothing is written (K7, M26; the M02 decision log). Tamper-evident
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

from quati.adapters.private_fs import (
    check_private_path, open_private, private_directory, read_private, state_directory, verify_entry, write_private)
from quati.behavior.fsutil import atomic_write
from quati.behavior.manifest import MANIFEST_FILE, PackageEntry, package_sha256, scan_package_dir
from quati.domain.canonical import canonical_bytes
from quati.domain.capability_registry import Refusal

STORE_SCHEMA = "quati-capability-store/1"
SECTIONS = ("records", "definitions", "bindings", "approvals", "history")
AUDIT_FILE = "audit.jsonl"
STORE_FILES = ("registry.json", "capabilities.lock", "registry.flock")      # the fixed files of the store
STORE_DIRECTORIES = ("packages", "staging")


class StoreChangeIncomplete(OSError):
    """A storage step that follows the registry commit failed: the change may have taken effect."""


def default_registry_root() -> Path:
    base = os.environ.get("QUATI_DATA_DIR") or str(Path.home() / ".quati")
    return Path(base) / "capabilities"


def empty_state() -> dict:
    return {"schema": STORE_SCHEMA, "revision": 0, **{name: [] for name in SECTIONS}}


def _audit_unavailable() -> Refusal:
    return Refusal("UNAVAILABLE", "TEMPORARILY_UNAVAILABLE", "audit_unavailable",
                   "The audit log is not a private, readable log of JSON events; nothing was read or recorded.")


def _events(raw: bytes) -> list[dict]:
    """The events of complete audit lines; a torn, non-JSON or non-object line raises ``ValueError``."""
    if raw and not raw.endswith(b"\n"):
        raise ValueError("audit log ends inside a line")
    events = [json.loads(line) for line in raw.splitlines() if line]
    if not all(isinstance(event, dict) for event in events):
        raise ValueError("audit line is not an object")
    return events


class FileRegistryStore:
    def __init__(self, root: Path, *, hook: Callable[[str], None] | None = None) -> None:
        self.root = Path(root)
        self.hook = hook
        self._lock_depth = 0
        self._audit_verified = 0                        # validated prefix of the audit log (ends at a line boundary)
        self._intent_logged = False                     # a registry.intent event was appended (write-ahead)
        self._change_committed = False                  # a commit followed such an intent
        self._packages_verified = False                 # verify_packages ran for this instance

    # ------------------------------------------------------------------ registry.json
    @property
    def registry_path(self) -> Path:
        return self.root / "registry.json"

    def _verified_root(self, *, create: bool) -> Path | None:
        """The registry root after the chain check; ``None`` for a reader when nothing is stored yet."""
        return state_directory(self.root.name, root=self.root.parent, create=create)

    def _directory(self, *parts: str, create: bool = True) -> Path | None:
        """The verified private directory ``<root>/parts...`` (each component in order), or ``None``."""
        return state_directory(self.root.name, *parts, root=self.root.parent, create=create)

    def prepare(self) -> None:
        """Verify, before a command logs its authorization decision, what can be verified without
        reading the registry: the directory chain (creating the root when missing), the ``packages``
        and ``staging`` directories, and the fixed store files by their metadata. The audit log is left
        to its own check (``verify_audit``, its own typed reason). Raises ``UnsafeStatePath``."""
        root = self._verified_root(create=True)
        for name in STORE_DIRECTORIES:
            self._directory(name, create=False)
        for name in STORE_FILES:
            check_private_path(root / name)

    def verify_packages(self) -> None:
        """Verify every directory and file of the stored and staged packages (a package id, a version
        and every directory inside a package are private directories, everything else a private regular
        file, the manifest included). Creates nothing; raises ``UnsafeStatePath``."""
        for name in STORE_DIRECTORIES:
            directory = self._directory(name, create=False)
            if directory is None:                       # nothing stored yet (or no store at all)
                continue
            for capability_id in sorted(os.listdir(directory)) if name == "packages" else ():
                self._directory(name, capability_id, create=False)
                for version in sorted(os.listdir(directory / capability_id)):
                    self._directory(name, capability_id, version, create=False)
            verify_entry(directory, files=frozenset({MANIFEST_FILE}))

    def _before_registry_use(self) -> None:
        """Once per store instance, before its first registry read or lock: ``verify_packages``."""
        if not self._packages_verified:
            self.verify_packages()
            self._packages_verified = True

    def load(self) -> dict:
        self._before_registry_use()
        raw = None if self._verified_root(create=False) is None else read_private(self.registry_path)
        return empty_state() if raw is None else json.loads(raw)

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
        self._verified_root(create=True)
        self._before_registry_use()
        with os.fdopen(open_private(self.root / "registry.flock", os.O_RDWR), "a+b") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            self._lock_depth = 1
            try:
                yield
            finally:
                self._lock_depth = 0
                fcntl.flock(handle, fcntl.LOCK_UN)

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
                         hook=self._committed, point="registry")
        return written

    def _committed(self, point: str) -> None:
        """Crash-injection hook of the registry write that also records the commit point."""
        if point == "registry.after_rename":
            self._change_committed = self._intent_logged
        if self.hook is not None:
            self.hook(point)

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
        # Everything that can fail for a storage reason happens here, before the registry commit: the
        # publish location is created and verified, then the staging copy is written.
        self._directory("packages", *self._package_id(entries))
        staging = self._directory("staging") / sha
        shutil.rmtree(staging, ignore_errors=True)
        private_directory(staging)
        for entry in entries:
            target = staging / entry.path
            private_directory(target.parent)
            write_private(target, entry.data)
        return sha, staging

    @staticmethod
    def _package_id(entries: tuple[PackageEntry, ...]) -> tuple[str, ...]:
        """``(capability id,)`` named by the staged manifest when it is one safe path component, else ``()``."""
        try:
            name = json.loads(next(entry.data for entry in entries if entry.path == MANIFEST_FILE))["id"]
        except (StopIteration, ValueError, KeyError, TypeError):
            return ()
        return (name,) if isinstance(name, str) and name not in ("", ".", "..") and name == Path(name).name else ()

    def publish_package(self, capability_id: str, version: str, staging: Path) -> None:
        """Rename a staged package into place; called only after the registry CAS committed, so a
        failure here is ``StoreChangeIncomplete`` (the location was verified by ``stage_package``)."""
        final = self.package_dir(capability_id, version)
        try:
            self._directory("packages", capability_id)
            if os.path.lexists(final):                  # an orphan or a tampered copy of the committed digest
                shutil.rmtree(final)
            os.replace(staging, final)
        except OSError as exc:
            raise StoreChangeIncomplete() from exc

    def discard_staging(self, staging: Path) -> None:
        shutil.rmtree(staging, ignore_errors=True)

    def read_package(self, capability_id: str, version: str) -> tuple[str, dict[str, bytes]] | None:
        """``(sha256, {path: bytes})`` from one scan of the stored package; ``None`` when unreadable."""
        try:
            self._verified_root(create=False)
            entries = scan_package_dir(self.package_dir(capability_id, version))
        except Exception:  # noqa: BLE001 - an unreadable stored package is a digest mismatch
            return None
        return package_sha256(entries), {entry.path: entry.data for entry in entries}

    def package_digest(self, capability_id: str, version: str) -> str | None:
        try:
            self._verified_root(create=False)
            return package_sha256(scan_package_dir(self.package_dir(capability_id, version)))
        except Exception:  # noqa: BLE001 - an unreadable stored package is a digest mismatch
            return None

    # ------------------------------------------------------------------ lock file
    @property
    def lock_path(self) -> Path:
        return self.root / "capabilities.lock"

    def lock_entries(self) -> list[dict]:
        raw = None if self._verified_root(create=False) is None else read_private(self.lock_path)
        return [] if raw is None else json.loads(raw)["entries"]

    def write_lock_entry(self, entry: dict) -> None:
        """Read-modify-write of ``capabilities.lock`` under the store lock; after a committed change a
        failure is ``StoreChangeIncomplete``."""
        try:
            with self._locked():
                self._write_lock_entry(entry)
        except OSError as exc:
            if self._change_committed:
                raise StoreChangeIncomplete() from exc
            raise

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
        return self.root / AUDIT_FILE

    def _audit_failure(self) -> Exception:
        """The typed failure of an audit read or append: after a committed change it says so."""
        return StoreChangeIncomplete() if self._change_committed else _audit_unavailable()

    def verify_audit(self) -> None:
        """Refuse with ``audit_unavailable`` unless the log is absent or a private log of JSON events
        (M01 Data directory rule 4); creates and changes nothing."""
        self.audit_events()

    def append_audit(self, event: dict) -> None:
        """Append one event to the private audit log, or refuse with ``audit_unavailable`` (fail closed).

        The log must be readable as a decision log before it grows: what this instance has not yet
        validated is parsed first, so an append never lands behind a torn or foreign line.
        """
        line = canonical_bytes(event) + b"\n"
        try:
            self._verified_root(create=True)
            raw = read_private(self.audit_path) or b""
            if len(raw) < self._audit_verified:         # replaced by a shorter log: validate all of it
                self._audit_verified = 0
            _events(raw[self._audit_verified:])
            descriptor = open_private(self.audit_path, os.O_WRONLY | os.O_APPEND)
            with os.fdopen(descriptor, "ab") as handle:
                handle.write(line)
                handle.flush()
                os.fsync(handle.fileno())
            self._audit_verified = len(raw)             # a line boundary; a concurrent writer may follow it
        except (OSError, ValueError):
            raise self._audit_failure() from None
        self._intent_logged = self._intent_logged or event.get("event") == "registry.intent"

    def audit_events(self) -> list[dict]:
        """Events of the private audit log; an unsafe, torn or non-JSON log is ``audit_unavailable``, never read."""
        try:
            if self._verified_root(create=False) is None:
                return []
            return _events(read_private(self.audit_path) or b"")
        except (OSError, ValueError):
            raise self._audit_failure() from None


__all__ = ["FileRegistryStore", "STORE_SCHEMA", "StoreChangeIncomplete", "default_registry_root", "empty_state"]
