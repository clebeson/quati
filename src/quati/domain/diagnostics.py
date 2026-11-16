"""Closed error-code list (BOUNDARY_CONTRACTS.md), typed contract diagnostics and the local-store exit rule."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


# M01 "Exit codes (stable)" rows 4 and 5: UNAVAILABLE whose ``data.reason`` names a local store (the audit
# log, the receipts, the data directory, the FeatureReport index) is not caused by a provider and exits 4;
# a provider failure exits 5. The one list: every use case that reports such a reason takes its exit code
# from ``settled_exit``.
LOCAL_STORE_REASONS = ("audit_unavailable", "audit_store_unavailable", "state_dir_unsafe",
                       "feature_report_not_stored")


def local_store_failure(value: dict) -> bool:
    """True when the Response ``value`` reports a failure of a local store, not of a provider."""
    data = value.get("data")
    return isinstance(data, dict) and data.get("reason") in LOCAL_STORE_REASONS


def settled_exit(code: int, value: dict) -> int:
    """The M01 exit code of a result whose table code is ``code``: a local store failure is 4, never 5.

    The one mapping used by the use cases and by the presentation boundary, so they cannot disagree."""
    return 4 if code == 5 and local_store_failure(value) else code


class ErrorCode(str, Enum):
    INVALID_INPUT = "INVALID_INPUT"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    FORBIDDEN = "FORBIDDEN"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    REVISION_CONFLICT = "REVISION_CONFLICT"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    NOT_FOUND = "NOT_FOUND"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    CONFIG_INVALID = "CONFIG_INVALID"
    UNSUPPORTED = "UNSUPPORTED"
    TEMPORARILY_UNAVAILABLE = "TEMPORARILY_UNAVAILABLE"
    DEADLINE_EXCEEDED = "DEADLINE_EXCEEDED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    OUTPUT_INVALID = "OUTPUT_INVALID"
    EVIDENCE_INSUFFICIENT = "EVIDENCE_INSUFFICIENT"
    EFFECT_UNCERTAIN = "EFFECT_UNCERTAIN"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass(frozen=True)
class Diagnostic:
    """One finding: closed code, dotted document path, detail reason tag, English message."""

    code: ErrorCode
    path: str
    reason: str
    message: str = ""

    def to_json(self) -> dict:
        return {"code": self.code.value, "path": self.path, "reason": self.reason, "message": self.message}


class ContractViolation(Exception):
    """A rejected input, carrying every diagnostic of the first failing rule class."""

    def __init__(self, diagnostics, rule_class: int | None = None) -> None:
        diagnostics = tuple(diagnostics)
        if not diagnostics:
            raise ValueError("a contract violation needs at least one diagnostic")
        self.diagnostics = diagnostics
        self.rule_class = rule_class
        first = diagnostics[0]
        super().__init__(f"{first.code.value} {first.reason} at {first.path}: {first.message}")

    @property
    def code(self) -> ErrorCode:
        return self.diagnostics[0].code

    @property
    def path(self) -> str:
        return self.diagnostics[0].path

    @property
    def reason(self) -> str:
        return self.diagnostics[0].reason


def violation(code: ErrorCode, reason: str, path: str = "$", message: str = "",
              rule_class: int | None = None) -> ContractViolation:
    return ContractViolation([Diagnostic(code, path, reason, message or reason)], rule_class)
