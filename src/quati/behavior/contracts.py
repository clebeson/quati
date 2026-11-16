"""Contract schemas and strict, safe parsing of declarative YAML/JSON (M30 rule class 1).

YAML is loaded with PyYAML's safe loader plus these rejections (all ``INVALID_INPUT``):
duplicate keys, explicit tags, anchors/aliases, non-string keys, several documents,
a non-mapping root, dates/timestamps and non-finite numbers, and oversize input.
JSON additionally rejects duplicate keys and ``NaN``/``Infinity``. Both reject nesting
deeper than ``MAX_DEPTH`` collections, integers beyond Python's digit limit and strings
that are not valid Unicode scalar sequences (lone surrogates). YAML nesting depth and
event count are bounded while streaming, before any object is constructed.

quati-json/1 forbids implicit numeric coercion: a schema ``integer`` never accepts a
float, not even an integer-valued one such as ``2.0``.
"""

from __future__ import annotations

from datetime import datetime
import functools
import hashlib
import importlib.resources
import json
import math
from pathlib import Path
import re
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker, validators

from quati.domain.diagnostics import ContractViolation, Diagnostic, ErrorCode

DEFAULT_MAX_BYTES = 1024 * 1024
MAX_DEPTH = 64
MAX_YAML_EVENTS = 100_000
PACKAGED_ASSETS = "assets"
# The asset files as (directory, pattern): exactly the ``tool.setuptools.package-data`` of pyproject.toml,
# so the same files are named in a wheel and in a source checkout.
ASSET_FILES = (("contracts", "*.json"), ("examples/behavior", "*.yaml"), ("examples/behavior", "*.json"),
               ("examples/statecharts", "*.yaml"), ("examples/policies", "*.json"))


def asset_root(package: Path | None = None) -> Path:
    """The directory that holds ``contracts/`` and ``examples/`` for the package directory ``package``.

    The repository layout wins (docs/architecture/PROJECT_STRUCTURE.md, asset locator rule): when the
    package is ``<root>/src/quati`` and ``<root>`` holds ``pyproject.toml``, ``contracts/`` and
    ``examples/``, this is a source checkout and ``<root>`` is used; an ``assets`` directory placed
    beside the package is then ignored and cannot shadow the repository files. Otherwise an installed
    wheel carries the files as package data in ``quati/assets`` (pyproject.toml,
    ``tool.setuptools.package-dir``). The files are the same bytes in both layouts and references stay
    relative to this root (``examples/behavior/...``), so no compiled hash depends on the layout.
    """
    if package is None:
        package = Path(str(importlib.resources.files("quati")))
    resolved = Path(package).resolve()
    checkout = resolved.parents[1]
    if resolved.parent.name == "src" and (checkout / "pyproject.toml").is_file() and all(
            (checkout / name).is_dir() for name in ("contracts", "examples")):
        return checkout
    packaged = Path(package) / PACKAGED_ASSETS
    return packaged if packaged.is_dir() else checkout


ASSET_ROOT = asset_root()
CONTRACTS_DIR = ASSET_ROOT / "contracts"


def asset_digest(root: Path | None = None) -> str:
    """SHA-256 over the sorted (root-relative POSIX path, file SHA-256) list of the asset files below
    ``root`` (default: the asset root in use): contract schemas, behavior packages, statecharts and
    policy templates. The one digest of the loaded assets (``quati doctor``, every receipt)."""
    root = ASSET_ROOT if root is None else Path(root)
    entries = sorted((path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest())
                     for directory, pattern in ASSET_FILES for path in (root / directory).glob(pattern)
                     if path.is_file())
    return hashlib.sha256(json.dumps(entries, separators=(",", ":")).encode("utf-8")).hexdigest()

FORMATS = FormatChecker()
_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})")


@FORMATS.checks("date-time")
def _date_time(value: object) -> bool:
    """RFC 3339 date-time with a mandatory offset (same rule as the reference compiler)."""
    if not isinstance(value, str):
        return True
    if not _TIMESTAMP.fullmatch(value):
        return False
    try:
        datetime.fromisoformat(value.upper().replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _strict_integer(checker, instance: object) -> bool:
    return isinstance(instance, int) and not isinstance(instance, bool)


StrictValidator = validators.extend(
    Draft202012Validator,
    type_checker=Draft202012Validator.TYPE_CHECKER.redefine("integer", _strict_integer))


class ContractCatalog:
    """Loads and caches the JSON Schemas under ``contracts/``."""

    def __init__(self, contracts_dir: Path | None = None) -> None:
        self.contracts_dir = Path(contracts_dir) if contracts_dir is not None else CONTRACTS_DIR
        self._validators: dict[str, Any] = {}

    def schema(self, schema_name: str) -> dict:
        return self._validator(schema_name).schema

    def _validator(self, schema_name: str):
        if schema_name not in self._validators:
            try:
                text = (self.contracts_dir / schema_name).read_text(encoding="utf-8")
            except OSError:
                # A broken installation (no contract schemas) is a typed diagnostic that names the schema
                # file and no local path; it is never an unhandled error of the command that needed it.
                raise ContractViolation([Diagnostic(
                    ErrorCode.NOT_FOUND, f"contracts/{schema_name}", "CONTRACT_NOT_FOUND",
                    f"contract schema {schema_name} is not installed")], 1) from None
            schema = json.loads(text)
            Draft202012Validator.check_schema(schema)
            self._validators[schema_name] = StrictValidator(schema, format_checker=FORMATS)
        return self._validators[schema_name]

    def errors(self, document: Any, schema_name: str) -> list:
        """All validation errors, in a deterministic order (by path, then message)."""
        found = self._validator(schema_name).iter_errors(document)
        return sorted(found, key=lambda error: (format_path(error_path(error)), error.message))


@functools.lru_cache(maxsize=1)
def default_catalog() -> ContractCatalog:
    return ContractCatalog()


def format_path(parts) -> str:
    text = ""
    for part in parts:
        text += f"[{part}]" if isinstance(part, int) else (f".{part}" if text else str(part))
    return text or "$"


def error_path(error) -> list:
    """Document path of a schema error; a missing required property is appended."""
    parts = list(error.absolute_path)
    if error.validator == "required" and isinstance(error.instance, dict):
        missing = [name for name in error.validator_value if name not in error.instance]
        parts.append(missing[0])
    return parts


def schema_violation(errors, *, code: ErrorCode = ErrorCode.INVALID_INPUT, reason: str = "SCHEMA_INVALID",
                     rule_class: int | None = 2) -> ContractViolation:
    return ContractViolation([Diagnostic(code, format_path(error_path(error)), reason, error.message)
                              for error in errors], rule_class)


class _Reject(Exception):
    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


def _parse_error(reason: str, message: str) -> ContractViolation:
    return ContractViolation([Diagnostic(ErrorCode.INVALID_INPUT, "$", reason, message)], 1)


def _text(data: bytes | str, max_bytes: int) -> str:
    raw = data.encode("utf-8") if isinstance(data, str) else bytes(data)
    if len(raw) > max_bytes:
        raise _Reject("TOO_LARGE", f"input exceeds {max_bytes} bytes")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        raise _Reject("PARSE_ERROR", "input is not valid UTF-8") from None


def _check_string(value: str) -> None:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise _Reject("INVALID_STRING", "strings must not contain lone surrogates") from None


def _check_values(value: Any, depth: int = 0) -> None:
    if isinstance(value, (dict, list)):
        depth += 1
        if depth > MAX_DEPTH:
            raise _Reject("PARSE_ERROR", f"nesting deeper than {MAX_DEPTH} levels")
        items = value.values() if isinstance(value, dict) else value
        for key in value if isinstance(value, dict) else ():
            if not isinstance(key, str):
                raise _Reject("NON_STRING_KEY", "mapping keys must be strings")
            _check_string(key)
        for item in items:
            _check_values(item, depth)
    elif isinstance(value, str):
        _check_string(value)
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise _Reject("UNSUPPORTED_VALUE", "non-finite numbers are not allowed")
    elif value is not None and not isinstance(value, (str, int)):
        raise _Reject("UNSUPPORTED_VALUE", f"{type(value).__name__} values are not allowed")


def check_document_values(document: Any) -> None:
    """Rule class 1 value check for in-memory documents (same rules as the parsers)."""
    try:
        _check_values(document)
    except _Reject as exc:
        raise _parse_error(exc.reason, str(exc)) from None


def _root(value: Any) -> dict:
    if not isinstance(value, dict):
        raise _Reject("NOT_A_MAPPING", "the document root must be a mapping")
    _check_values(value)
    return value


class _UniqueKeyLoader(yaml.SafeLoader):
    """Safe loader whose mappings reject duplicate and non-string keys."""


def _unique_mapping(loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False) -> dict:
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        if not isinstance(key, str):
            raise _Reject("NON_STRING_KEY", "mapping keys must be strings")
        if key in result:
            raise _Reject("DUPLICATE_KEY", f"duplicate key {key!r}")
        result[key] = loader.construct_object(value_node, deep=True)
    return result


_UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping)


def _scan_events(text: str) -> None:
    documents = depth = 0
    for count, event in enumerate(yaml.parse(text, Loader=yaml.SafeLoader), 1):
        if count > MAX_YAML_EVENTS:
            raise _Reject("PARSE_ERROR", f"more than {MAX_YAML_EVENTS} YAML events")
        if isinstance(event, yaml.CollectionStartEvent):
            depth += 1
            if depth > MAX_DEPTH:
                raise _Reject("PARSE_ERROR", f"nesting deeper than {MAX_DEPTH} levels")
        elif isinstance(event, yaml.CollectionEndEvent):
            depth -= 1
        if isinstance(event, yaml.AliasEvent) or getattr(event, "anchor", None) is not None:
            raise _Reject("ALIAS_FORBIDDEN", "YAML anchors and aliases are not allowed")
        if getattr(event, "tag", None) is not None:
            raise _Reject("TAG_FORBIDDEN", "explicit YAML tags are not allowed")
        if isinstance(event, yaml.DocumentStartEvent):
            documents += 1
            if documents > 1:
                raise _Reject("PARSE_ERROR", "exactly one YAML document is allowed")


def parse_yaml(data: bytes | str, *, max_bytes: int = DEFAULT_MAX_BYTES) -> dict:
    try:
        text = _text(data, max_bytes)
        _scan_events(text)
        return _root(yaml.load(text, Loader=_UniqueKeyLoader))
    except _Reject as exc:
        raise _parse_error(exc.reason, str(exc)) from None
    except (yaml.YAMLError, RecursionError, ValueError) as exc:  # ValueError: integer digit limit
        raise _parse_error("PARSE_ERROR", f"invalid YAML: {type(exc).__name__}") from None


def _unique_pairs(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise _Reject("DUPLICATE_KEY", f"duplicate key {key!r}")
        result[key] = value
    return result


def _no_constant(name: str):
    raise _Reject("UNSUPPORTED_VALUE", f"{name} is not allowed")


def parse_json(data: bytes | str, *, max_bytes: int = DEFAULT_MAX_BYTES) -> dict:
    try:
        text = _text(data, max_bytes)
        return _root(json.loads(text, object_pairs_hook=_unique_pairs, parse_constant=_no_constant))
    except _Reject as exc:
        raise _parse_error(exc.reason, str(exc)) from None
    except (ValueError, RecursionError) as exc:
        raise _parse_error("PARSE_ERROR", f"invalid JSON: {type(exc).__name__}") from None


def parse_document(name: str, data: bytes | str, *, max_bytes: int = DEFAULT_MAX_BYTES) -> dict:
    """Parse by file suffix: ``.yaml``/``.yml`` or ``.json``; anything else is unsupported."""
    suffix = Path(name).suffix.lower()
    if suffix in (".yaml", ".yml"):
        return parse_yaml(data, max_bytes=max_bytes)
    if suffix == ".json":
        return parse_json(data, max_bytes=max_bytes)
    raise _parse_error("UNSUPPORTED_FORMAT", f"unsupported file type {suffix or '(none)'}")
