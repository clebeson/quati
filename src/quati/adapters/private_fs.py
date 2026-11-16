"""Owner-only local state: private directories and no-follow private files (LOCAL trust boundary).

The same rule ``config/`` and ``receipts/`` follow: a state directory is a real directory (never a
symlink) owned by the current user with mode 0700, and a state file is a regular, singly linked
file owned by the current user with no group or other permission bit. A path that cannot be made
or proven private raises ``UnsafeStatePath`` (an ``OSError`` whose ``filename`` is the path) so the
caller fails closed; nothing is written elsewhere. A file is opened without following a symlink and
without blocking, so a FIFO can never hang a command; a wider file mode is refused, never repaired.
A writer removes the wider bits of a directory the user owns and never adds a permission: a
directory that lacks an owner bit is refused (docs/prds/M01.md, Data directory rule 1).

``state_directory`` is the one entry every store uses before it reads, locks, writes or appends:
it verifies the data directory (``QUATI_DATA_DIR``) and each Quati directory under it, in order,
so nothing is created or changed below a component that is a symlink or belongs to another user.
"""

from __future__ import annotations

import errno
import os
import stat
from pathlib import Path

DIRECTORY_MODE = 0o700
FILE_MODE = 0o600


class UnsafeStatePath(PermissionError):
    """A Quati state path that is not (and cannot be made) a private path of the current user."""


def _refuse(path: Path, why: str) -> OSError:
    return UnsafeStatePath(errno.EPERM, f"{why}: not a private Quati state path", str(path))


def data_root() -> Path:
    """The data directory: ``QUATI_DATA_DIR`` or ``~/.quati``."""
    return Path(os.environ.get("QUATI_DATA_DIR") or Path.home() / ".quati")


def _verify(path: Path, tighten: bool) -> None:
    """Refuse ``path`` unless it is a real directory of this user; decide on one no-follow descriptor.

    The owner of the path as named is checked first, so a foreign path is never opened. The open
    itself refuses a symlink and anything that is not a directory (``O_NOFOLLOW | O_DIRECTORY``);
    owner and mode are then read from, and the mode is tightened on, the open descriptor, so a path
    swapped after the first check cannot redirect the decision or the mode change (LOG-0041 N17).
    """
    if os.lstat(path).st_uid != os.getuid():
        raise _refuse(path, "foreign owner")
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError:
        raise _refuse(path, "symlink, non-directory or unreadable directory") from None
    try:
        info = os.fstat(descriptor)
        if info.st_uid != os.getuid():
            raise _refuse(path, "foreign owner")
        mode = stat.S_IMODE(info.st_mode)
        if not tighten:
            if mode & 0o077:
                raise _refuse(path, "group or other permission bits")
        elif mode & DIRECTORY_MODE != DIRECTORY_MODE:
            raise _refuse(path, "owner permission bits missing")
        elif mode != DIRECTORY_MODE:
            os.fchmod(descriptor, DIRECTORY_MODE)
    finally:
        os.close(descriptor)


def private_directory(path: Path, *, tighten: bool = True) -> Path:
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
    _verify(path, tighten)
    return path


def state_directory(*parts: str, root: Path | None = None, create: bool = True, tighten: bool = True) -> Path | None:
    """The verified private directory ``root/parts...`` (``root`` defaults to the data directory).

    ``root`` and then each component are verified in order before the next one is touched: a real
    directory, never a symlink (nor below a symlinked ancestor), owned by the current user, mode
    0700. ``create`` makes missing components (a writer); without it a missing component returns
    ``None`` and nothing is created (a reader). ``tighten`` removes wider permission bits of an owned
    directory; without it they are refused and nothing is modified. Anything else raises
    ``UnsafeStatePath``.
    """
    current = Path(root) if root is not None else data_root()
    if any(ancestor.is_symlink() for ancestor in current.parents):
        raise _refuse(current, "symlinked ancestor")
    for part in (None, *parts):
        current = current if part is None else current / part
        if not create and not os.path.lexists(current):
            return None
        private_directory(current, tighten=tighten)
    return current


def private_tree(path: Path) -> Path:
    """Make an existing tree owner-only (directories 0700, files 0600) without following any symlink.

    For a tree written by code that uses the process umask (``data/fixture_sources``). A symlink, a
    special file, an extra hard link or a foreign owner anywhere in it raises ``UnsafeStatePath``.
    """
    path = Path(path)
    _verify(path, True)
    for entry in sorted(path.iterdir()):
        if entry.is_dir() and not entry.is_symlink():
            private_tree(entry)
        else:
            os.close(_checked(_open(entry, os.O_RDONLY), entry, True))
    return path


def verify_entry(entry: Path, *, files: frozenset[str] = frozenset()) -> None:
    """Refuse ``entry`` unless it is a private regular file or a tree of private directories and files.

    A directory is verified like every state directory (wider bits removed) and then entry by entry;
    anything else, and any entry whose name is in ``files`` whatever its type, must be a private regular
    file. Nothing is created; an entry removed meanwhile by another Quati process is skipped.
    """
    entry = Path(entry)
    try:
        if entry.name in files or not stat.S_ISDIR(os.lstat(entry).st_mode):
            check_private_file(entry)
            return
        _verify(entry, True)
        names = sorted(os.listdir(entry))
    except FileNotFoundError:
        return
    for name in names:
        verify_entry(entry / name, files=files)


def _open(path: Path, flags: int) -> int:
    """Open without following a symlink and without blocking; what cannot be opened is not private."""
    try:
        return os.open(path, flags | os.O_NOFOLLOW | os.O_NONBLOCK, FILE_MODE)
    except FileNotFoundError:
        raise
    except OSError:
        raise _refuse(Path(path), "symlink or file that cannot be opened") from None


def _wider(info: os.stat_result, path: Path) -> bool:
    """Refuse unless ``info`` is a singly linked regular file of this user; True when it has wider bits."""
    if not stat.S_ISREG(info.st_mode):
        raise _refuse(path, "not a regular file")
    if info.st_uid != os.getuid() or info.st_nlink != 1:
        raise _refuse(path, "foreign owner or extra hard link")
    return bool(stat.S_IMODE(info.st_mode) & 0o077)


def _checked(descriptor: int, path: Path, tighten: bool) -> int:
    try:
        if _wider(os.fstat(descriptor), path):
            if not tighten:
                raise _refuse(path, "group or other permission bits")
            os.fchmod(descriptor, FILE_MODE)
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def check_private_path(path: Path) -> None:
    """Refuse ``path`` by its metadata, without opening it, unless it is absent or a private regular file.

    The early check of a store file that a command has not been authorized to read yet: no open, so a
    FIFO cannot block and nothing is read. The descriptor check of ``read_private`` / ``open_private``
    stays the authority when the file is used.
    """
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return
    if _wider(info, Path(path)):
        raise _refuse(Path(path), "group or other permission bits")


def open_private(path: Path, flags: int) -> int:
    """Open (creating with mode 0600) without following a symlink; refuse any file that is not private."""
    return _checked(_open(path, flags | os.O_CREAT), Path(path), False)


def read_private(path: Path) -> bytes | None:
    """The bytes of a private file read without following a symlink; ``None`` when it does not exist."""
    try:
        descriptor = _open(path, os.O_RDONLY)
    except FileNotFoundError:
        return None
    with os.fdopen(_checked(descriptor, Path(path), False), "rb") as handle:
        return handle.read()


def check_private_file(path: Path) -> None:
    """Refuse ``path`` unless it is absent or a private regular file; nothing is read or changed."""
    try:
        descriptor = _open(path, os.O_RDONLY)
    except FileNotFoundError:
        return
    os.close(_checked(descriptor, Path(path), False))


def write_private(path: Path, data: bytes) -> None:
    """Create a new private file holding ``data``; an existing path is an error."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, FILE_MODE)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)


__all__ = ["DIRECTORY_MODE", "FILE_MODE", "UnsafeStatePath", "check_private_file", "check_private_path",
           "data_root", "open_private",
           "private_directory", "private_tree", "read_private", "state_directory", "verify_entry", "write_private"]
