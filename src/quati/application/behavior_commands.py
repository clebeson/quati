"""Public compiler use cases behind ``quati behavior validate|render`` (M30 Public interface, S00).

Both use cases authenticate first (M02 authorization order row 1), then compile the named package
with the deterministic ``BehaviorCompiler`` against the kernel baseline trusted-policy slot. They
read only the package file and the statechart it references inside the package root, call no
provider and write nothing. A rejected package is a typed ``CONFIG_INVALID`` Response that carries
the compiler's field/path-specific diagnostics unchanged (CMP-02, CMP-03).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from quati.application.cli_service import response
from quati.behavior.compiler import BehaviorCompiler, PromptArtifact
from quati.domain.diagnostics import ContractViolation, ErrorCode, violation

HASHES = ("behavior_hash", "statechart_hash", "prompt_hash")
INVALID_MESSAGE = "The behavior package or its statechart failed validation."
INVALID_NEXT_ACTION = ("Correct the fields named in data.diagnostics, then run `quati behavior validate` again; "
                       "nothing was compiled, stored or activated.")


def diagnostic_lines(exc: ContractViolation) -> list[str]:
    """One stable line per diagnostic: closed code, reason tag and document path."""
    return [f"{item.code.value} {item.reason} at {item.path}" for item in exc.diagnostics]


def rejection(exc: ContractViolation) -> dict:
    """The ValidationReport fields of a rejected package."""
    return {"ok": False, "rule_class": exc.rule_class, "build_digest": None, "receipt": None,
            "diagnostics": [item.to_json() for item in exc.diagnostics]}


def package_ref(package: str, root: Path) -> str:
    """``package`` as a reference inside ``root``: relative as given, absolute only when under ``root``."""
    if not os.path.isabs(package):
        return package
    try:
        return Path(package).relative_to(Path(root).absolute()).as_posix()
    except ValueError:
        raise violation(ErrorCode.FORBIDDEN, "PATH_TRAVERSAL", "profile_ref",
                        "the package is outside the package root", 3) from None


def active_package_status(root: Path, profile_ref: str, model_role_ref: str | None = None) -> dict:
    """Doctor's view of the active behavior package: VALID with its hashes, or INVALID with diagnostics."""
    status = {"profile_ref": profile_ref, "status": "VALID", "diagnostics": []}
    try:
        artifact = BehaviorCompiler(root).compile(profile_ref, model_role_ref=model_role_ref)
    except ContractViolation as exc:
        return {**status, "status": "INVALID", "rule_class": exc.rule_class,
                "diagnostics": [item.to_json() for item in exc.diagnostics]}
    return {**status, **{name: artifact.receipt[name] for name in HASHES}, "build_digest": artifact.build_digest}


class BehaviorCommands:
    def __init__(self, identity, compiler_factory: Callable[[Path], BehaviorCompiler] = BehaviorCompiler) -> None:
        self.identity = identity
        self.compiler_factory = compiler_factory

    def _compile(self, package: str, root: str) -> tuple[str, PromptArtifact | ContractViolation]:
        self.identity.authenticate()
        reference = package
        try:
            reference = package_ref(package, Path(root))
            return reference, self.compiler_factory(Path(root)).compile(reference)
        except ContractViolation as exc:
            return reference, exc

    @staticmethod
    def _rejected(reference: str, exc: ContractViolation) -> tuple[int, dict]:
        return 2, response("DENIED", {"package": reference, **rejection(exc)}, "CONFIG_INVALID", INVALID_MESSAGE,
                            INVALID_NEXT_ACTION, diagnostic_lines(exc))

    def validate(self, package: str, root: str) -> tuple[int, dict]:
        """M30 ``validate``: the ValidationReport with the deterministic receipt hashes."""
        reference, outcome = self._compile(package, root)
        if isinstance(outcome, ContractViolation):
            return self._rejected(reference, outcome)
        receipt = outcome.receipt
        return 0, response("SUCCEEDED", {"package": reference, "ok": True, "rule_class": None, "diagnostics": [],
                                          "build_digest": outcome.build_digest, "receipt": receipt,
                                          **{name: receipt[name] for name in HASHES}})

    def render(self, package: str, root: str) -> tuple[int, dict]:
        """M30 ``render`` in S00: compile the package and return its PromptArtifact (English preview)."""
        reference, outcome = self._compile(package, root)
        if isinstance(outcome, ContractViolation):
            return self._rejected(reference, outcome)
        return 0, response("SUCCEEDED", {"package": reference, **outcome.to_document()})


__all__ = ["BehaviorCommands", "active_package_status", "diagnostic_lines", "package_ref", "rejection"]
