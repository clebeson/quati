"""Crash-safe local file writes with named crash-injection points."""

from __future__ import annotations

from contextlib import contextmanager
import fcntl
import itertools
import os
from pathlib import Path
from typing import Callable, Iterator

CrashHook = Callable[[str], None]
_COUNTER = itertools.count()


def atomic_write(path: Path, data: bytes, *, hook: CrashHook | None = None, point: str = "write") -> None:
    """Write ``.tmp-*`` (no ``.json`` suffix), fsync, rename; the temp file never survives a failure.

    ``hook(f"{point}.before_rename")`` runs after fsync and ``hook(f"{point}.after_rename")``
    after the rename, so tests can crash at either side of the commit point.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".tmp-{os.getpid()}-{next(_COUNTER)}"
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if hook is not None:
            hook(f"{point}.before_rename")
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    if hook is not None:
        hook(f"{point}.after_rename")


@contextmanager
def locked(path: Path) -> Iterator[None]:
    """Hold an exclusive ``flock`` on the sibling ``<path>.lock`` (cross-process CAS section)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(f"{path}.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)  # closing the descriptor releases the lock
