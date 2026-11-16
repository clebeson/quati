"""M14-FR-01 SCS capability manifest validation and the RFC-015 package digest.

Every rejection is ``INVALID_INPUT`` with the first failing reason of
``MANIFEST_REASON_ORDER``. Schema errors are mapped to reasons by their schema
location, so a specific reason is never shadowed by the generic schema check unless
a generic (unknown field, wrong type) error is also present.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path, PurePosixPath
import stat
from typing import Any, Iterable

from jsonschema import Draft202012Validator, SchemaError

from quati.behavior.contracts import ContractCatalog, default_catalog, parse_json
from quati.domain.diagnostics import ErrorCode, violation

SCHEMA_NAME = "scs-capability.schema.json"
MANIFEST_FILE = "capability.scs.json"
MAX_PACKAGE_BYTES = 1048576
MANIFEST_REASON_ORDER = (
    "MANIFEST_SCHEMA_INVALID", "ID_INVALID", "VERSION_NOT_SEMVER", "INTENTS_INSUFFICIENT",
    "SCHEMA_NO_PROPERTIES", "REMOTE_REF", "OUTCOME_CONTRACT_MISSING", "DESTINATIONS_MISSING",
    "OUTCOME_VERIFICATION_MISSING", "APPROVAL_FLAG_INCONSISTENT", "SYMLINK_IN_PACKAGE", "PATH_TRAVERSAL",
)
ENTRY_KINDS = ("file", "symlink", "special")


def _reason_for(error) -> str:
    """Map a schema error to its M14 reason by the schema keyword location."""
    location = list(error.absolute_schema_path)
    head = location[:2]
    if head[0] == "allOf":
        if location[1] == 0:
            return "APPROVAL_FLAG_INCONSISTENT"
        if error.validator == "required":
            # One error per missing property; destinations precede verification in the order.
            return "DESTINATIONS_MISSING" if "destinations" not in error.instance else "OUTCOME_VERIFICATION_MISSING"
        return "OUTCOME_VERIFICATION_MISSING" if "outcome_verification" in location else "DESTINATIONS_MISSING"
    if head[0] == "properties":
        return {"id": "ID_INVALID", "version": "VERSION_NOT_SEMVER", "intents": "INTENTS_INSUFFICIENT",
                "input_schema": "SCHEMA_NO_PROPERTIES", "output_schema": "SCHEMA_NO_PROPERTIES",
                "outcomes": "OUTCOME_CONTRACT_MISSING", "evaluation": "OUTCOME_CONTRACT_MISSING",
                }.get(head[1], "MANIFEST_SCHEMA_INVALID")
    if error.validator == "required":
        missing = [name for name in error.validator_value if name not in error.instance]
        return {"intents": "INTENTS_INSUFFICIENT", "input_schema": "SCHEMA_NO_PROPERTIES",
                "output_schema": "SCHEMA_NO_PROPERTIES", "outcomes": "OUTCOME_CONTRACT_MISSING",
                "evaluation": "OUTCOME_CONTRACT_MISSING"}.get(missing[0], "MANIFEST_SCHEMA_INVALID")
    return "MANIFEST_SCHEMA_INVALID"


def _refs(value: Any) -> Iterable[Any]:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in ("$ref", "$dynamicRef"):
                yield item
            yield from _refs(item)
    elif isinstance(value, list):
        for item in value:
            yield from _refs(item)


def _escapes(ref: str) -> bool:
    path = ref.split("#", 1)[0]
    return path.startswith("/") or ".." in PurePosixPath(path).parts or "\\" in path


def validate_manifest(manifest: Any, *, catalog: ContractCatalog | None = None) -> None:
    """Raise ``INVALID_INPUT`` with the first failing M14 reason; return None when valid."""
    catalog = catalog or default_catalog()
    reasons = {_reason_for(error) for error in catalog.errors(manifest, SCHEMA_NAME)}
    if isinstance(manifest, dict):
        for field in ("input_schema", "output_schema"):
            nested = manifest.get(field)
            if isinstance(nested, dict):
                try:
                    Draft202012Validator.check_schema(nested)
                except SchemaError:
                    reasons.add("MANIFEST_SCHEMA_INVALID")
                if isinstance(nested.get("properties"), dict) and not nested["properties"]:
                    reasons.add("SCHEMA_NO_PROPERTIES")
                if any(not isinstance(ref, str) or not ref.startswith("#") for ref in _refs(nested)):
                    reasons.add("REMOTE_REF")
        evaluation = manifest.get("evaluation")
        if isinstance(evaluation, list) and any(isinstance(ref, str) and _escapes(ref) for ref in evaluation):
            reasons.add("PATH_TRAVERSAL")
    else:
        reasons.add("MANIFEST_SCHEMA_INVALID")
    if reasons:
        first = min(reasons, key=MANIFEST_REASON_ORDER.index)
        raise violation(ErrorCode.INVALID_INPUT, first, "$", f"capability manifest rejected: {first}")


@dataclass(frozen=True)
class PackageEntry:
    path: str
    kind: str
    data: bytes

    def __post_init__(self) -> None:
        if self.kind not in ENTRY_KINDS:
            raise ValueError(f"entry kind must be one of {ENTRY_KINDS}")


def _normalized(path: str) -> bool:
    if not path or path.startswith("/") or "\\" in path:
        return False
    return all(part not in ("", ".", "..") for part in path.split("/"))


def package_sha256(entries: Iterable[PackageEntry]) -> str:
    """RFC-015: hash of ``path \\0 sha256(bytes) \\n`` over the bytewise-sorted regular files."""
    entries = list(entries)
    checks = (
        ("SYMLINK_IN_PACKAGE", lambda e: e.kind == "symlink"),
        ("NOT_REGULAR_FILE", lambda e: e.kind == "special"),
        ("PATH_TRAVERSAL", lambda e: not _normalized(e.path)),
    )
    for reason, failed in checks:
        bad = [entry.path for entry in entries if failed(entry)]
        if bad:
            raise violation(ErrorCode.INVALID_INPUT, reason, "$", f"package entry rejected: {bad[0]!r}")
    paths = [entry.path for entry in entries]
    if len(set(paths)) != len(paths):
        raise violation(ErrorCode.INVALID_INPUT, "DUPLICATE_PATH", "$", "package lists a path twice")
    hasher = hashlib.sha256()
    for entry in sorted(entries, key=lambda e: e.path.encode("utf-8")):
        hasher.update(entry.path.encode("utf-8") + b"\0" + hashlib.sha256(entry.data).hexdigest().encode() + b"\n")
    return hasher.hexdigest()


def _read_regular(path: Path) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as handle:
        return handle.read()


def scan_package_dir(root: Path, *, max_package_bytes: int = MAX_PACKAGE_BYTES) -> tuple[PackageEntry, ...]:
    """List the package without following symlinks; sizes are bounded before reading."""
    root = Path(root)
    try:
        root_stat = os.lstat(root)
    except FileNotFoundError:
        raise violation(ErrorCode.NOT_FOUND, "PACKAGE_NOT_FOUND", "$", "package directory not found") from None
    if stat.S_ISLNK(root_stat.st_mode):
        raise violation(ErrorCode.INVALID_INPUT, "SYMLINK_IN_PACKAGE", "$", "package root is a symlink")
    if not stat.S_ISDIR(root_stat.st_mode):
        raise violation(ErrorCode.NOT_FOUND, "PACKAGE_NOT_FOUND", "$", "package root is not a directory")
    found: list[tuple[str, str, Path]] = []
    total = 0
    for directory, subdirectories, files in os.walk(root, followlinks=False):
        subdirectories.sort()
        for name in sorted(subdirectories + files):
            full = Path(directory) / name
            mode = os.lstat(full).st_mode
            relative = full.relative_to(root).as_posix()
            if stat.S_ISDIR(mode):
                continue
            kind = "symlink" if stat.S_ISLNK(mode) else "file" if stat.S_ISREG(mode) else "special"
            if kind == "file":
                total += os.lstat(full).st_size
            found.append((relative, kind, full))
    if total > max_package_bytes:
        raise violation(ErrorCode.INVALID_INPUT, "PACKAGE_TOO_LARGE", "$",
                        f"package exceeds {max_package_bytes} bytes")
    return tuple(PackageEntry(relative, kind, _read_regular(full) if kind == "file" else b"")
                 for relative, kind, full in sorted(found, key=lambda item: item[0].encode("utf-8")))


@dataclass(frozen=True)
class CapabilityPackage:
    manifest: dict
    package_sha256: str
    entries: tuple[PackageEntry, ...]


def load_capability_package(root: Path, *, max_package_bytes: int = MAX_PACKAGE_BYTES,
                            catalog: ContractCatalog | None = None) -> CapabilityPackage:
    """Scan, validate the sidecar (M14 order), then compute the digest (symlink/traversal last)."""
    entries = scan_package_dir(root, max_package_bytes=max_package_bytes)
    sidecar = [entry for entry in entries if entry.path == MANIFEST_FILE]
    if not sidecar:
        raise violation(ErrorCode.INVALID_INPUT, "MANIFEST_MISSING", "$", f"{MANIFEST_FILE} is required")
    if sidecar[0].kind != "file":
        raise violation(ErrorCode.INVALID_INPUT, "SYMLINK_IN_PACKAGE", MANIFEST_FILE,
                        f"{MANIFEST_FILE} must be a regular file")
    manifest = parse_json(sidecar[0].data, max_bytes=max_package_bytes)
    validate_manifest(manifest, catalog=catalog)
    return CapabilityPackage(manifest, package_sha256(entries), entries)
