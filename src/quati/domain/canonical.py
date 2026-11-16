"""quati-json/1 canonical form and digest.

The canonical bytes are ``json.dumps(value, sort_keys=True, separators=(",", ":"),
ensure_ascii=True, allow_nan=False)`` encoded as ASCII. This is a project-defined
rule (not RFC 8785); it matches ``spec_tools/behavior_compiler.py`` and RFC-014
``policy_version``. Only JSON-native values are accepted.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

CANONICAL_RULE = "quati-json/1"


class CanonicalJsonError(ValueError):
    """The value has no quati-json/1 canonical form."""


def _check(value: Any) -> None:
    if value is None or isinstance(value, (bool, str, int)):
        return
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise CanonicalJsonError("non-finite number")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalJsonError("mapping keys must be strings")
            _check(item)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _check(item)
        return
    raise CanonicalJsonError(f"unsupported value type {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    _check(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def is_digest(value: Any) -> bool:
    return (isinstance(value, str) and len(value) == 64
            and all(character in "0123456789abcdef" for character in value))
