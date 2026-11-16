"""Measured facts about this process and host for the M01 ``DoctorReport`` (read-only).

Nothing here is inferred: the operating system and interpreter are read from the running
interpreter, the SQLite library version and its FTS5 option from the linked library, and the
number of listening sockets from this process's own open descriptors. S00 has no ledger database,
so the journal mode cannot be measured and is reported as the explicit ``NOT_VERIFIED`` value.
"""

from __future__ import annotations

import os
import platform
import socket
import sqlite3
import stat
from pathlib import Path

REFERENCE_OS = "Linux"            # M01-AT-01: the only OS qualified so far
KNOWN_OS = ("Linux", "Darwin", "Windows")


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


def collect(config_dir: Path) -> dict:
    system = platform.system()
    fts5 = sqlite_fts5()
    return {"os": system, "os_qualification": os_qualification(system),
            "python_version": platform.python_version(),
            "sqlite_version": sqlite3.sqlite_version, "sqlite_fts5": fts5, "sqlite_ok": fts5,
            "sqlite_journal_mode": "NOT_VERIFIED", "sqlite_journal_reason": "ledger_not_delivered",
            "config_dir": str(config_dir), "listening_sockets": listening_sockets()}


__all__ = ["collect", "listening_sockets", "os_qualification", "sqlite_fts5"]
