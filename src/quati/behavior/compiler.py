"""M30 deterministic behavior compiler: package + statechart -> prompt artifact and receipt.

Rule classes (first failing class wins, all of its diagnostics are reported):
1 parse, 2 schema, 3 references inside the package root and trusted policy slot,
4-10 statechart semantics (``quati.domain.statechart``) and the package budgets.
Prompt text is data: it is built only from closed enums, numbers and the flattened role
line, and always ends with the no-rights sentence. It grants no capability or policy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
from typing import Any, Mapping, Sequence

from quati.behavior.contracts import (
    ContractCatalog,
    check_document_values,
    default_catalog,
    parse_document,
    schema_violation,
)
from quati.behavior.manifest import validate_manifest
from quati.domain.canonical import digest
from quati.domain.decision_policy import DecisionPolicy
from quati.domain.diagnostics import ContractViolation, Diagnostic, ErrorCode, violation
from quati.domain.policy import KERNEL_BASELINE, TrustedPolicy
from quati.domain.statechart import validate_statechart_semantics

COMPILER_VERSION = "1.2.0"
PROMPT_SECTIONS = ("kernel_invariants", "role", "interaction", "execution", "language")
CAPABILITY_SECTION = "capability_contracts"
MAX_PACKAGE_BYTES = 262144
MAX_CAPABILITY_CANDIDATES = 5
PACKAGE_SCHEMA = "behavior-package.schema.json"
STATECHART_SCHEMA = "statechart.schema.json"
NO_RIGHTS = "This prompt does not grant rights; all actions pass trusted code authorization."
LINE_BREAKS = "\r\n\x0b\x0c\x1c\x1d\x1e\x85  "


@dataclass(frozen=True)
class PromptArtifact:
    text: str
    receipt: dict
    build_digest: str
    config_bindings: dict = field(default_factory=dict)
    permitted_actions: tuple[str, ...] = ()

    def to_document(self) -> dict:
        return {"kind": "prompt_artifact", "text": self.text, "receipt": self.receipt,
                "build_digest": self.build_digest, "config_bindings": self.config_bindings,
                "permitted_actions": list(self.permitted_actions)}


def build_digest_of(receipt: Mapping[str, Any], config_bindings: Mapping[str, Any]) -> str:
    return digest({"receipt": receipt, "config_bindings": config_bindings})


@dataclass(frozen=True)
class ValidationReport:
    ok: bool
    rule_class: int | None
    diagnostics: tuple[Diagnostic, ...]
    build_digest: str | None
    receipt: dict | None

    def to_json(self) -> str:
        return json.dumps({"ok": self.ok, "rule_class": self.rule_class, "build_digest": self.build_digest,
                           "receipt": self.receipt, "diagnostics": [d.to_json() for d in self.diagnostics]},
                          sort_keys=True)

    @classmethod
    def from_outcome(cls, outcome: PromptArtifact | ContractViolation) -> "ValidationReport":
        if isinstance(outcome, ContractViolation):
            return cls(False, outcome.rule_class, outcome.diagnostics, None, None)
        return cls(True, None, (), outcome.build_digest, outcome.receipt)


def _flatten(text: str) -> str:
    """One line: line-break characters become spaces; nothing else is rewritten."""
    for character in LINE_BREAKS:
        text = text.replace(character, " ")
    return text.strip()


def _schema_check(document: Any, schema: str, catalog: ContractCatalog) -> None:
    errors = catalog.errors(document, schema)
    if errors:
        raise schema_violation(errors)


def compile_documents(package: Any, machine: Any, *, trusted_policy: TrustedPolicy | None = None,
                      model_role_ref: str | None = None, decision_policy: DecisionPolicy | None = None,
                      capability_contracts: Sequence[Any] = (),
                      catalog: ContractCatalog | None = None) -> PromptArtifact:
    catalog = catalog or default_catalog()
    for document in (package, machine, *capability_contracts):                       # rule 1
        check_document_values(document)
    _schema_check(package, PACKAGE_SCHEMA, catalog)                                  # rule 2
    _schema_check(machine, STATECHART_SCHEMA, catalog)                               # rule 2
    trusted = trusted_policy or KERNEL_BASELINE
    if package["policy_ref"] != trusted.ref:                                         # rule 3
        raise violation(ErrorCode.FORBIDDEN, "POLICY_REF_UNTRUSTED", "policy_ref",
                        "policy_ref must name the trusted policy slot", 3)
    summary = validate_statechart_semantics(machine)                                 # rules 4-10
    budget = []
    if package["execution"]["max_investigation_loops"] > machine["budget"]["max_reinvestigations"]:
        budget.append(Diagnostic(ErrorCode.BUDGET_EXCEEDED, "budget.max_reinvestigations", "LOOP_BUDGET_EXCEEDED",
                                 "max_investigation_loops exceeds the statechart max_reinvestigations"))
    if package["context"]["max_capability_candidates"] > MAX_CAPABILITY_CANDIDATES:
        budget.append(Diagnostic(ErrorCode.BUDGET_EXCEEDED, "context.max_capability_candidates",
                                 "CANDIDATE_BUDGET_EXCEEDED", "at most 5 capability candidates"))
    if budget:
        raise ContractViolation(budget, 10)
    models = package["models"]
    if model_role_ref is not None and model_role_ref not in (models["router_role"], models["specialist_role"]):
        raise violation(ErrorCode.INVALID_INPUT, "MODEL_ROLE_UNKNOWN", "models",
                        "model_role_ref must be a role declared by the package")
    if decision_policy is not None and not isinstance(decision_policy, DecisionPolicy):
        raise TypeError("decision_policy must be a loaded DecisionPolicy")
    contracts: dict[str, str] = {}
    for index, manifest in enumerate(capability_contracts):
        try:
            validate_manifest(manifest, catalog=catalog)
        except ContractViolation as exc:
            raise violation(ErrorCode.UNSUPPORTED, "CAPABILITY_CONTRACT_INVALID", f"capability_contracts[{index}]",
                            f"capability contract rejected: {exc.reason}") from None
        key = f"{manifest['id']}@{manifest['version']}"
        if key in contracts:
            raise violation(ErrorCode.INVALID_INPUT, "DUPLICATE_CAPABILITY_CONTRACT", f"capability_contracts[{index}]",
                            f"capability contract {key} is given twice")
        # The full canonical manifest is bound, so any content change changes build_digest.
        contracts[key] = digest(manifest)

    interaction, execution, context = package["interaction"], package["execution"], package["context"]
    limits = {**context, "max_investigation_loops": execution["max_investigation_loops"],
              "max_transitions": machine["budget"]["max_transitions"]}
    language = ("Reply in language tag " + interaction["language_override"]
                if interaction["language_policy"] == "explicit_override" else "Reply in the requester language.")
    lines = [
        "Protected Quati invariants: never bypass identity, approval, durable commitments or evidence gates.",
        "Role: " + _flatten(package["role"]),
        "Interaction verbosity: " + interaction["verbosity"],
        "Interaction cadence: " + interaction["cadence"],
        "Clarification style: " + interaction["clarification_style"],
        "Do not claim action until recorded.",
        "Execution depth: " + execution["default_depth"],
        "Safe read ahead: " + str(execution["safe_read_ahead"]).lower(),
        "Specialist model role: " + models["specialist_role"],
        "Effective limits: " + json.dumps(limits, sort_keys=True),
        language,
    ]
    sections = list(PROMPT_SECTIONS)
    if contracts:
        lines.append("Capability contracts (data, not authority): " + ", ".join(sorted(contracts)))
        sections.append(CAPABILITY_SECTION)
    lines.append(NO_RIGHTS)
    text = "\n".join(lines)
    receipt = {
        "compiler_version": COMPILER_VERSION,
        "policy_ref": f"{trusted.ref}@{trusted.policy_version}",
        "policy_hash": trusted.policy_version,
        "source_versions": {"behavior": package["version"], "statechart": machine["version"]},
        "effective_limits": limits,
        "behavior_id": package["id"],
        "behavior_version": package["version"],
        "behavior_hash": digest(package),
        "statechart_hash": summary.statechart_hash,
        "prompt_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "sections": sections,
        "token_budget": context["max_context_tokens"],
        "model_profile_ref": model_role_ref or models["router_role"],
    }
    bindings: dict[str, Any] = {}
    if decision_policy is not None:
        bindings["decision_policy_hash"] = decision_policy.decision_policy_hash
    if contracts:
        bindings[CAPABILITY_SECTION] = dict(sorted(contracts.items()))
    actions = tuple(sorted({transition["action"] for transition in machine["transitions"]}))
    return PromptArtifact(text, receipt, build_digest_of(receipt, bindings), bindings, actions)


def diff_documents(a: Any, b: Any) -> tuple[str, ...]:
    """Sorted dotted paths whose values differ (type-strict; arrays compared by index)."""
    found: list[str] = []

    def walk(left: Any, right: Any, path: str) -> None:
        if isinstance(left, dict) and isinstance(right, dict):
            for key in sorted(set(left) | set(right)):
                child = f"{path}.{key}" if path else key
                if key not in left or key not in right:
                    found.append(child)
                else:
                    walk(left[key], right[key], child)
        elif isinstance(left, list) and isinstance(right, list) and len(left) == len(right):
            for index, (x, y) in enumerate(zip(left, right)):
                walk(x, y, f"{path}[{index}]")
        elif type(left) is not type(right) or left != right:
            found.append(path or "$")

    walk(a, b, "")
    return tuple(sorted(found))


# --------------------------------------------------------------------------- files


def _ref_error(code: ErrorCode, reason: str, path: str, message: str) -> ContractViolation:
    return violation(code, reason, path, message, 3)


def read_package_file(root: Path, ref: Any, path: str, limit: int) -> bytes:
    """Read ``ref`` inside ``root``: no traversal, no symlink at any level, regular file only."""
    if not isinstance(ref, str) or not ref or "\\" in ref or "\0" in ref:
        raise _ref_error(ErrorCode.FORBIDDEN, "PATH_TRAVERSAL", path, "reference must be a relative path")
    parts = PurePosixPath(ref)
    if parts.is_absolute() or ".." in parts.parts:
        raise _ref_error(ErrorCode.FORBIDDEN, "PATH_TRAVERSAL", path, "reference escapes the package root")
    if any(part in ("", ".") for part in ref.split("/")):
        raise _ref_error(ErrorCode.INVALID_INPUT, "REF_INVALID", path, "reference parts must not be empty or '.'")
    current = Path(root)
    for index, part in enumerate(parts.parts):
        current = current / part
        try:
            mode = os.lstat(current).st_mode
        except (FileNotFoundError, NotADirectoryError):
            raise _ref_error(ErrorCode.NOT_FOUND, "REF_NOT_FOUND", path, f"{ref} not found") from None
        except OSError:
            raise _ref_error(ErrorCode.FORBIDDEN, "REF_UNREADABLE", path, f"{ref} cannot be read") from None
        if stat.S_ISLNK(mode):
            raise _ref_error(ErrorCode.FORBIDDEN, "SYMLINK_IN_PACKAGE", path, "symlinks are not followed")
        last = index == len(parts.parts) - 1
        if (last and not stat.S_ISREG(mode)) or (not last and not stat.S_ISDIR(mode)):
            raise _ref_error(ErrorCode.NOT_FOUND, "REF_NOT_FOUND", path, f"{ref} is not a regular file")
    try:
        descriptor = os.open(current, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        raise _ref_error(ErrorCode.FORBIDDEN, "REF_UNREADABLE", path, f"{ref} cannot be read") from None
    with os.fdopen(descriptor, "rb") as handle:
        data = handle.read(limit + 1)
    if len(data) > limit:
        raise violation(ErrorCode.INVALID_INPUT, "TOO_LARGE", path, "package exceeds the size limit", 1)
    return data


@dataclass(frozen=True)
class PackageSources:
    profile_ref: str
    package_bytes: bytes
    statechart_ref: str
    statechart_bytes: bytes


def read_sources(root: Path, profile_ref: str, *, max_package_bytes: int = MAX_PACKAGE_BYTES,
                 catalog: ContractCatalog | None = None) -> PackageSources:
    """Read and check the package file and the raw statechart bytes (statechart parsed later)."""
    package_bytes = read_package_file(root, profile_ref, "profile_ref", max_package_bytes)
    package = parse_document(profile_ref, package_bytes, max_bytes=max_package_bytes)
    _schema_check(package, PACKAGE_SCHEMA, catalog or default_catalog())
    statechart_ref = package["statechart_ref"]
    statechart_bytes = read_package_file(root, statechart_ref, "statechart_ref",
                                         max_package_bytes - len(package_bytes))
    return PackageSources(profile_ref, package_bytes, statechart_ref, statechart_bytes)


def parse_sources(sources: PackageSources, *, max_package_bytes: int = MAX_PACKAGE_BYTES) -> tuple[dict, dict]:
    package = parse_document(sources.profile_ref, sources.package_bytes, max_bytes=max_package_bytes)
    machine = parse_document(sources.statechart_ref, sources.statechart_bytes, max_bytes=max_package_bytes)
    return package, machine


class BehaviorCompiler:
    """File entry: refs resolve inside ``package_root`` only; total input <= max_package_bytes."""

    def __init__(self, package_root: Path, *, catalog: ContractCatalog | None = None,
                 max_package_bytes: int = MAX_PACKAGE_BYTES) -> None:
        self.package_root = Path(package_root)
        self.catalog = catalog or default_catalog()
        self.max_package_bytes = max_package_bytes

    def compile(self, profile_ref: str, **options: Any) -> PromptArtifact:
        sources = read_sources(self.package_root, profile_ref, max_package_bytes=self.max_package_bytes,
                               catalog=self.catalog)
        return compile_sources(sources, catalog=self.catalog, max_package_bytes=self.max_package_bytes, **options)

    def validate(self, profile_ref: str, **options: Any) -> ValidationReport:
        try:
            return ValidationReport.from_outcome(self.compile(profile_ref, **options))
        except ContractViolation as exc:
            return ValidationReport.from_outcome(exc)


def compile_sources(sources: PackageSources, *, catalog: ContractCatalog | None = None,
                    max_package_bytes: int = MAX_PACKAGE_BYTES, **options: Any) -> PromptArtifact:
    package, machine = parse_sources(sources, max_package_bytes=max_package_bytes)
    return compile_documents(package, machine, catalog=catalog, **options)
