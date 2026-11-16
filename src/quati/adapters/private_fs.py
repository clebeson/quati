"""Owner-only local state: private directories and no-follow private files (LOCAL trust boundary).

The same rule ``config/`` and ``receipts/`` follow: a state directory is a real directory (never a
symlink) owned by the current user with mode 0700, and a state file is a regular, singly linked
file owned by the current user with no group or other permission bit. A path that cannot be made
or proven private raises ``OSError`` so the caller fails closed; nothing is written elsewhere.
"""

from __future__ import annotations

import errno
import os
import stat
from pathlib import Path

DIRECTORY_MODE = 0o700
FILE_MODE = 0o600


def _refuse(path: Path, why: str) -> OSError:
    return PermissionError(errno.EPERM, f"{why}: not a private Quati state path", str(path))


def private_directory(path: Path) -> Path:
    """Create ``path`` and its missing ancestors with mode 0700; tighten or refuse an existing one."""
    path = Path(path)
    missing = []
    current = path
    while not os.path.lexists(current):
        missing.append(current)
        current = current.parent
    for directory in reversed(missing):
        try:
            os.mkdir(directory, DIRECTORY_MODE)
        except FileExistsError:           # created concurrently by another Quati process; checked below
            pass
    info = os.lstat(path)
    if not stat.S_ISDIR(info.st_mode):
        raise _refuse(path, "symlink or non-directory")
    if info.st_uid != os.getuid():
        raise _refuse(path, "foreign owner")
    if stat.S_IMODE(info.st_mode) != DIRECTORY_MODE:
        os.chmod(path, DIRECTORY_MODE)
    return path


def _checked(descriptor: int, path: Path, tighten: bool) -> int:
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise _refuse(path, "not a regular file")
        if info.st_uid != os.getuid() or info.st_nlink != 1:
            raise _refuse(path, "foreign owner or extra hard link")
        if stat.S_IMODE(info.st_mode) & 0o077:
            if not tighten:
                raise _refuse(path, "group or other permission bits")
            os.fchmod(descriptor, FILE_MODE)
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def open_private(path: Path, flags: int, *, tighten: bool = False) -> int:
    """Open (creating with mode 0600) without following a symlink; refuse any file that is not private.

    ``tighten`` is for content-free files (a lock file): wider permission bits left by an older
    version are removed instead of refused. A file whose content must be trusted is never tightened.
    """
    descriptor = os.open(path, flags | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, FILE_MODE)
    return _checked(descriptor, Path(path), tighten)


def read_private(path: Path) -> bytes | None:
    """The bytes of a private file read without following a symlink; ``None`` when it does not exist."""
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None
    with os.fdopen(_checked(descriptor, Path(path), False), "rb") as handle:
        return handle.read()


def write_private(path: Path, data: bytes) -> None:
    """Create a new private file holding ``data``; an existing path is an error."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, FILE_MODE)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)


__all__ = ["DIRECTORY_MODE", "FILE_MODE", "open_private", "private_directory", "read_private", "write_private"]
