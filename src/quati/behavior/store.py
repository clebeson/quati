"""S00 local, content-addressed behavior store: propose -> validate -> promote/rollback.

Layout under ``root``::

    objects/<sha256>.json     source objects and compiled prompt artifacts (immutable)
    proposals/<digest>.json   proposal records (canonical bytes; digest = sha256 of them)
    reports/<digest>.json     latest validation report of a proposal
    active/<behavior_id>.json active pointer: digest, revision, history, consumed approvals
    locks/<behavior_id>.json.lock flock file serializing pointer compare-and-swap

A model proposal is stored as data only; activation needs a passing validation and a
single-use HUMAN approval bound to the exact build digest, checked by code before the
trusted approval verifier is consulted, plus a compare-and-swap on the pointer revision.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Callable, Iterable, Mapping

from quati.behavior.compiler import (
    MAX_PACKAGE_BYTES,
    PackageSources,
    PromptArtifact,
    ValidationReport,
    build_digest_of,
    compile_sources,
    diff_documents,
    parse_sources,
    read_sources,
)
from quati.behavior.contracts import ContractCatalog, default_catalog, parse_json
from quati.behavior.fsutil import CrashHook, atomic_write, locked
from quati.domain.canonical import canonical_bytes, digest, is_digest
from quati.domain.diagnostics import ContractViolation, Diagnostic, ErrorCode, violation
from quati.domain.statechart import Step, next_state

ORIGINS = ("OPERATOR", "MODEL")
BEHAVIOR_ID = re.compile(r"^[a-z][a-z0-9_.-]+$")


def _no_hook(name: str) -> None:
    return None


@dataclass(frozen=True)
class Proposal:
    digest: str
    origin: str
    author: str
    profile_ref: str
    statechart_ref: str
    package_object: str
    statechart_object: str


@dataclass(frozen=True)
class ActivePointer:
    behavior_id: str
    active_digest: str | None
    revision: int
    history: tuple[str, ...]
    consumed_approvals: tuple[str, ...] = ()


@dataclass(frozen=True)
class PromotionApproval:
    """Reference to a trusted approval record (the ApprovalPort arrives in S02)."""

    approval_id: str
    approver_id: str
    approver_kind: str
    artifact_digest: str
    expires_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.approval_id, str) or not self.approval_id:
            raise ValueError("approval_id is required")
        if not isinstance(self.expires_at, datetime) or self.expires_at.tzinfo is None:
            raise ValueError("expires_at must be a timezone-aware datetime")


def _check_digest(value: Any) -> str:
    if not is_digest(value):
        raise violation(ErrorCode.INVALID_INPUT, "DIGEST_INVALID", "$", "expected a sha256 hex digest")
    return value


class BehaviorStore:
    def __init__(self, root: Path, *, catalog: ContractCatalog | None = None,
                 crash_hook: CrashHook | None = None, max_package_bytes: int = MAX_PACKAGE_BYTES) -> None:
        self.root = Path(root)
        self.catalog = catalog or default_catalog()
        self.hook = crash_hook or _no_hook
        self.max_package_bytes = max_package_bytes

    # ------------------------------------------------------------------ objects

    def _write(self, path: Path, data: bytes, point: str) -> None:
        atomic_write(path, data, hook=self.hook, point=point)

    def _put_object(self, document: Mapping[str, Any], point: str, name: str | None = None) -> str:
        data = canonical_bytes(document)
        name = name or hashlib.sha256(data).hexdigest()
        path = self.root / "objects" / f"{name}.json"
        if not path.exists():
            self._write(path, data, point)
        return f"{name}.json"

    def _get_source(self, object_name: str) -> bytes:
        data = (self.root / "objects" / object_name).read_bytes()
        if f"{hashlib.sha256(data).hexdigest()}.json" != object_name:
            raise violation(ErrorCode.INTERNAL_ERROR, "DIGEST_MISMATCH", "$", "stored source object was altered")
        return base64.b64decode(json.loads(data)["content_b64"])

    def _read_json(self, path: Path, missing: ContractViolation) -> dict:
        try:
            data = path.read_bytes()
        except FileNotFoundError:
            raise missing from None
        try:
            return parse_json(data)
        except ContractViolation:
            raise violation(ErrorCode.INTERNAL_ERROR, "OBJECT_CORRUPT", "$", f"{path.name} is corrupt") from None

    # ------------------------------------------------------------------ proposals

    def propose(self, package_root: Path, profile_ref: str, *, origin: str, author: str) -> Proposal:
        if origin not in ORIGINS:
            raise violation(ErrorCode.INVALID_INPUT, "ORIGIN_INVALID", "origin", "origin must be OPERATOR or MODEL")
        if not isinstance(author, str) or not author.strip():
            raise violation(ErrorCode.INVALID_INPUT, "AUTHOR_MISSING", "author", "author is required")
        sources = read_sources(Path(package_root), profile_ref, max_package_bytes=self.max_package_bytes,
                               catalog=self.catalog)
        package_object = self._put_source(sources.profile_ref, sources.package_bytes)
        statechart_object = self._put_source(sources.statechart_ref, sources.statechart_bytes)
        record = {"kind": "proposal", "origin": origin, "author": author, "profile_ref": sources.profile_ref,
                  "statechart_ref": sources.statechart_ref, "package_object": package_object,
                  "statechart_object": statechart_object}
        proposal_digest = digest(record)
        path = self.root / "proposals" / f"{proposal_digest}.json"
        if not path.exists():
            self._write(path, canonical_bytes(record), "store.write_proposal")
        return Proposal(proposal_digest, origin, author, sources.profile_ref, sources.statechart_ref,
                        package_object, statechart_object)

    def _put_source(self, name: str, data: bytes) -> str:
        document = {"kind": "source", "name": name, "content_b64": base64.b64encode(data).decode("ascii")}
        return self._put_object(document, "store.write_source")

    def _proposal(self, proposal_digest: str) -> Proposal:
        _check_digest(proposal_digest)
        record = self._read_json(self.root / "proposals" / f"{proposal_digest}.json",
                                 violation(ErrorCode.NOT_FOUND, "UNKNOWN_PROPOSAL", "$", "unknown proposal"))
        if digest(record) != proposal_digest:
            raise violation(ErrorCode.INTERNAL_ERROR, "DIGEST_MISMATCH", "$", "proposal record was altered")
        return Proposal(proposal_digest, record["origin"], record["author"], record["profile_ref"],
                        record["statechart_ref"], record["package_object"], record["statechart_object"])

    def _sources(self, proposal: Proposal) -> PackageSources:
        return PackageSources(proposal.profile_ref, self._get_source(proposal.package_object),
                              proposal.statechart_ref, self._get_source(proposal.statechart_object))

    def validate(self, proposal_digest: str) -> ValidationReport:
        sources = self._sources(self._proposal(proposal_digest))  # integrity errors raise, never "reject"
        try:
            artifact = compile_sources(sources, catalog=self.catalog,
                                       max_package_bytes=self.max_package_bytes)
        except ContractViolation as exc:
            report, behavior_id = ValidationReport.from_outcome(exc), None
        else:
            self._put_object(artifact.to_document(), "store.write_object", name=artifact.build_digest)
            report, behavior_id = ValidationReport.from_outcome(artifact), artifact.receipt["behavior_id"]
        self.hook("store.validate.before_report")
        record = json.loads(report.to_json())
        record["behavior_id"] = behavior_id
        self._write(self.root / "reports" / f"{proposal_digest}.json", canonical_bytes(record), "store.write_report")
        return report

    def _report(self, proposal_digest: str) -> dict | None:
        path = self.root / "reports" / f"{proposal_digest}.json"
        if not path.exists():
            return None
        return self._read_json(path, violation(ErrorCode.NOT_FOUND, "UNKNOWN_REPORT", "$", "report missing"))

    def proposal_state(self, proposal_digest: str) -> str:
        self._proposal(proposal_digest)
        report = self._report(proposal_digest)
        if report is None:
            return "PROPOSED"
        if not report["ok"]:
            return "REJECTED"
        pointer = self.active(report["behavior_id"])
        if pointer.active_digest == report["build_digest"]:
            return "ACTIVE"
        if report["build_digest"] in pointer.history:
            return "SUPERSEDED"
        return "VALIDATED"

    # ------------------------------------------------------------------ artifacts

    def render(self, build_digest: str) -> PromptArtifact:
        _check_digest(build_digest)
        document = self._read_json(self.root / "objects" / f"{build_digest}.json",
                                   violation(ErrorCode.NOT_FOUND, "ARTIFACT_NOT_FOUND", "$", "unknown artifact"))
        try:
            artifact = PromptArtifact(document["text"], document["receipt"], document["build_digest"],
                                      document["config_bindings"], tuple(document["permitted_actions"]))
            intact = (hashlib.sha256(artifact.text.encode("utf-8")).hexdigest() == artifact.receipt["prompt_hash"]
                      and build_digest_of(artifact.receipt, artifact.config_bindings) == build_digest
                      and artifact.build_digest == build_digest)
        except (KeyError, TypeError, AttributeError):
            intact = False
        if not intact:
            raise violation(ErrorCode.INTERNAL_ERROR, "DIGEST_MISMATCH", "$", "stored artifact was altered")
        return artifact

    def simulate(self, proposal_digest: str, events: Iterable[tuple[str, Mapping[str, Any]]]) -> tuple[Step, ...]:
        """Run the trusted reducer over a stored proposal's statechart."""
        proposal = self._proposal(proposal_digest)
        sources = self._sources(proposal)
        compile_sources(sources, catalog=self.catalog, max_package_bytes=self.max_package_bytes)
        _, machine = parse_sources(sources, max_package_bytes=self.max_package_bytes)
        state, used, trace = machine["initial"], 0, []
        for event, guard_results in events:
            step = next_state(machine, state, event, guard_results=guard_results, transitions_used=used)
            if step.accepted:
                state, used = step.state, used + 1
            trace.append(step)
        return tuple(trace)

    def diff(self, first: str, second: str) -> tuple[str, ...]:
        documents = []
        for proposal_digest in (first, second):
            package, machine = parse_sources(self._sources(self._proposal(proposal_digest)),
                                             max_package_bytes=self.max_package_bytes)
            documents.append({"package": package, "statechart": machine})
        return diff_documents(*documents)

    # ------------------------------------------------------------------ pointers

    def active(self, behavior_id: str) -> ActivePointer:
        if not isinstance(behavior_id, str) or not BEHAVIOR_ID.fullmatch(behavior_id):
            raise violation(ErrorCode.INVALID_INPUT, "BEHAVIOR_ID_INVALID", "behavior_id", "invalid behavior id")
        path = self.root / "active" / f"{behavior_id}.json"
        if not path.exists():
            return ActivePointer(behavior_id, None, 0, ())
        record = self._read_json(path, violation(ErrorCode.NOT_FOUND, "POINTER_MISSING", "$", "pointer missing"))
        return ActivePointer(record["behavior_id"], record["active_digest"], record["revision"],
                             tuple(record["history"]), tuple(record["consumed_approvals"]))

    def _pointer_lock(self, behavior_id: str):
        """Exclusive lock on ``locks/<id>.json.lock`` around read-compare-replace (cross-process)."""
        return locked(self.root / "locks" / f"{behavior_id}.json")

    def _swap(self, pointer: ActivePointer, target: str, consumed: tuple[str, ...]) -> ActivePointer:
        history = pointer.history + ((pointer.active_digest,) if pointer.active_digest else ())
        updated = ActivePointer(pointer.behavior_id, target, pointer.revision + 1, history, consumed)
        record = {"behavior_id": updated.behavior_id, "active_digest": updated.active_digest,
                  "revision": updated.revision, "history": list(updated.history),
                  "consumed_approvals": list(updated.consumed_approvals)}
        self._write(self.root / "active" / f"{pointer.behavior_id}.json", canonical_bytes(record),
                    "store.write_pointer")
        return updated

    def promote(self, proposal_digest: str, *, approval: PromotionApproval | None, expected_revision: int,
                now: datetime, verify_approval: Callable[[PromotionApproval], bool]) -> ActivePointer:
        if now.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        self._proposal(proposal_digest)
        report = self._report(proposal_digest)
        if report is None:
            raise violation(ErrorCode.FORBIDDEN, "VALIDATION_REQUIRED", "$", "validate the proposal first")
        if not report["ok"]:
            raise violation(ErrorCode.FORBIDDEN, "PROPOSAL_REJECTED", "$", "a rejected proposal cannot be promoted")
        build_digest = report["build_digest"]

        def refuse(reason: str, message: str):
            return violation(ErrorCode.FORBIDDEN, reason, "approval", message)

        if approval is None:
            raise violation(ErrorCode.APPROVAL_REQUIRED, "approval_missing", "approval", "a human approval is required")
        if approval.approver_kind != "HUMAN":
            raise refuse("approver_not_human", "AGENT and SERVICE principals never approve")
        if approval.artifact_digest != build_digest:
            raise refuse("binding_mismatch:artifact_digest", "approval is bound to another artifact")
        if now >= approval.expires_at:
            raise refuse("approval_expired", "approval has expired")
        with self._pointer_lock(report["behavior_id"]):
            pointer = self.active(report["behavior_id"])
            if approval.approval_id in pointer.consumed_approvals:
                raise refuse("approval_consumed", "approval was already used")
            if verify_approval(approval) is not True:
                raise refuse("approval_not_trusted", "approval is not in the trusted approval store")
            if expected_revision != pointer.revision:
                raise violation(ErrorCode.REVISION_CONFLICT, "REVISION_CONFLICT", "expected_revision",
                                "active pointer revision changed")
            self.render(build_digest)
            return self._swap(pointer, build_digest, pointer.consumed_approvals + (approval.approval_id,))

    def rollback(self, behavior_id: str, target_digest: str, *, expected_revision: int) -> ActivePointer:
        _check_digest(target_digest)
        self.active(behavior_id)  # validates the id before it names a lock file
        with self._pointer_lock(behavior_id):
            pointer = self.active(behavior_id)
            if target_digest == pointer.active_digest or target_digest not in pointer.history:
                raise violation(ErrorCode.NOT_FOUND, "NEVER_ACTIVE", "target_digest",
                                "rollback target was never a previous active version")
            if expected_revision != pointer.revision:
                raise violation(ErrorCode.REVISION_CONFLICT, "REVISION_CONFLICT", "expected_revision",
                                "active pointer revision changed")
            self.render(target_digest)
            return self._swap(pointer, target_digest, pointer.consumed_approvals)


__all__ = ["ActivePointer", "BehaviorStore", "Diagnostic", "PromotionApproval", "Proposal"]
