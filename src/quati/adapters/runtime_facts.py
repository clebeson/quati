"""Measured facts about this process and host for the M01 ``DoctorReport`` (read-only).

Nothing here is inferred: the operating system and interpreter are read from the running
interpreter, the SQLite library version and its FTS5 option from the linked library, and the
number of listening sockets from this process's own open descriptors. S00 has no ledger database,
so the journal mode cannot be measured and is reported as the explicit ``NOT_VERIFIED`` value.
"""

from __future__ import annotations

import json
import os
import platform
import socket
import sqlite3
import stat
from pathlib import Path

from quati.adapters.local_identity import IDENTIFIER_FIELDS

REFERENCE_OS = "Linux"            # M01-AT-01: the only OS qualified so far
KNOWN_OS = ("Linux", "Darwin", "Windows")
# The installation-record fields every S00 command reads (RFC-013 section 4); each is a non-empty string:
# the identifiers the identity adapter itself requires (``LocalIdentity._load``) and the device public key.
RECORD_FIELDS = (*IDENTIFIER_FIELDS, "public_key")
RECORD_MAX_BYTES = 16384


def os_qualification(system: str) -> str:
    if system == REFERENCE_OS:
        return "QUALIFIED"
    return "NOT_VERIFIED" if system in KNOWN_OS else "UNSUPPORTED"


def sqlite_fts5() -> bool:
    """True when the linked SQLite can create an FTS5 table (what the S00 capability index needs)."""
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE VIRTUAL TABLE probe USING fts5(text)")
    except sqlite3.Error:
        return False
    finally:
        connection.close()
    return True


def _descriptors() -> list[int]:
    try:
        return [int(name) for name in os.listdir("/proc/self/fd")]
    except (OSError, ValueError):
        return list(range(0, 1024))


def listening_sockets() -> int:
    """Number of this process's open descriptors that are sockets in the listening state."""
    count = 0
    for descriptor in _descriptors():
        try:
            if not stat.S_ISSOCK(os.fstat(descriptor).st_mode):
                continue
            duplicate = os.dup(descriptor)
        except OSError:
            continue
        try:
            handle = socket.socket(fileno=duplicate)
        except OSError:
            os.close(duplicate)
            continue
        with handle:
            try:
                count += bool(handle.getsockopt(socket.SOL_SOCKET, socket.SO_ACCEPTCONN))
            except OSError:
                continue
    return count


def record_complete(record) -> bool:
    """True when ``record`` is an installation record that carries every field S00 reads."""
    return isinstance(record, dict) and all(
        isinstance(record.get(name), str) and record[name] for name in RECORD_FIELDS)


def _insecure_entry(path: Path, label: str, directory: bool = False) -> str | None:
    """The M02 ``credential_insecure`` detail of one existing path (symlink, type, owner, extra hard link
    of a file, mode), or None."""
    info = os.lstat(path)
    if stat.S_ISLNK(info.st_mode):
        return f"{label}_symlink"
    if not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)):
        return f"{label}_not_directory" if directory else f"{label}_not_regular"
    if info.st_uid != os.getuid():
        return f"{label}_owner"
    if not directory and info.st_nlink != 1:
        return f"{label}_hard_link"
    return f"{label}_mode" if stat.S_IMODE(info.st_mode) & 0o077 else None


def _record_detail(path: Path) -> str:
    """Why a private installation record is not accepted: not JSON, a missing field, or rejected as signed."""
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as stream:
            raw = stream.read(RECORD_MAX_BYTES + 1)
        record = json.loads(raw) if len(raw) <= RECORD_MAX_BYTES else None
    except (OSError, ValueError, RecursionError):
        return "record_not_json"
    if not isinstance(record, dict):
        return "record_not_json"
    return "record_rejected" if record_complete(record) else "record_field_missing"


def identity_state(config_dir: Path) -> dict:
    """Why the LOCAL identity adapter does not accept the credential under ``config_dir`` (M02 reason table).

    Called only after the adapter reported no usable identity. ``present`` is false when no
    credential exists (``credential_missing``: run ``quati init``). Otherwise the credential is
    present but rejected: ``credential_insecure`` (symlink, owner or mode of the directory or of a
    credential file) or ``credential_corrupt`` (a file is missing, the record is not JSON, lacks a
    field, or is complete but was rejected by the adapter: signature, key or owner mismatch).
    ``detail`` is a stable tag; no path and no file content is returned. Nothing is modified.
    """
    def state(cause, detail=None):
        return {"present": cause != "credential_missing", "cause": cause, "detail": detail}

    directory = Path(config_dir)
    if os.environ.get("QUATI_CAPABILITY_CONTEXT"):      # a capability invocation is shown no credential state
        return state("credential_missing")
    if any(part.is_symlink() for part in (directory, *directory.parents)):
        return state("credential_insecure", "config_dir_symlink")
    if not os.path.lexists(directory):
        return state("credential_missing")
    detail = _insecure_entry(directory, "config_dir", directory=True)
    if detail:
        return state("credential_insecure", detail)
    files = (("identity_file", directory / "identity.json"), ("device_key", directory / "device.key"))
    existing = [(label, path) for label, path in files if os.path.lexists(path)]
    if not existing:
        return state("credential_missing")
    for label, path in existing:
        detail = _insecure_entry(path, label)
        if detail:
            return state("credential_insecure", detail)
    if len(existing) < len(files):
        return state("credential_corrupt", next(f"{label}_missing" for label, path in files
                                                 if not os.path.lexists(path)))
    return state("credential_corrupt", _record_detail(directory / "identity.json"))


def collect(config_dir: Path) -> dict:
    system = platform.system()
    fts5 = sqlite_fts5()
    return {"os": system, "os_qualification": os_qualification(system),
            "python_version": platform.python_version(),
            "sqlite_version": sqlite3.sqlite_version, "sqlite_fts5": fts5, "sqlite_ok": fts5,
            "sqlite_journal_mode": "NOT_VERIFIED", "sqlite_journal_reason": "ledger_not_delivered",
            "config_dir": str(config_dir), "listening_sockets": listening_sockets()}


__all__ = ["RECORD_FIELDS", "collect", "identity_state", "listening_sockets", "os_qualification", "record_complete",
           "sqlite_fts5"]
