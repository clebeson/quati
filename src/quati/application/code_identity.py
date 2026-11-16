"""Digest of Quati's own Python code (audit P2-E): a rewritten use case must change a receipt digest."""

from __future__ import annotations

import functools
import hashlib
import json
from pathlib import Path

import quati


def code_digest(root: Path) -> str:
    """sha256 over the sorted (POSIX relative path, file sha256) list of every ``.py`` file under ``root``."""
    root = Path(root)
    entries = sorted((path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest())
                     for path in root.rglob("*.py") if path.is_file())
    return hashlib.sha256(json.dumps(entries, separators=(",", ":")).encode("utf-8")).hexdigest()


@functools.lru_cache(maxsize=1)
def current_code_digest() -> str:
    """The running package's digest, computed once per process."""
    return code_digest(Path(quati.__file__).resolve().parent)


__all__ = ["code_digest", "current_code_digest"]
