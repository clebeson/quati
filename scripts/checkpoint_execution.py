#!/usr/bin/env python3
"""Record resumable active_work progress with revision CAS and a recoverable hash chain.

The same journaled event may also carry one slice patch: gate statuses, per-gate
seal references resolved from the seal index, the slice commit, evidence
references and blockers. A gate becomes PASS only with indexed, hash-verified
TESTS_VERIFIED and EVIDENCE_VERIFIED seal records whose scope covers the gate or
its slice, and a recorded slice commit. A seal whose index record names a
referenced seal in `supersedes` replaces that reference for the gate. This helper checks the seal locator, the
record hash, identity, scope and verdict; full provenance validation remains in
spec_tools/validate_readiness.py.

The JSONL ledger is an engineering execution journal, not Quati's product ledger.
This bounded POSIX advisory flock serializes only writers using this helper and
the same state sidecar inode. Writers that do not take this lock are outside its
concurrency protection. The OS releases it on process exit; it is not a stale
lease and does not claim cross-host or non-POSIX concurrency safety.
"""

import argparse
import fcntl
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

PHASES = {"DISCOVER", "SDD", "TDD_RED", "IMPLEMENT", "EDD", "AUDIT", "CHECKPOINT"}
IMPLEMENTATION_PHASES = {"TDD_RED", "IMPLEMENT", "EDD"}
WORK_MODES = {"SPECIFICATION_ONLY", "IMPLEMENTATION_AUTHORIZED"}
DEFAULT_STATE = Path(__file__).resolve().parents[1] / "docs/implementation/implementation_state.json"
DEFAULT_LEDGER = DEFAULT_STATE.with_name("execution_ledger.jsonl")
DEFAULT_SEAL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEAL_INDEX = DEFAULT_SEAL_ROOT / "governance/seals/index.json"
GATE_STATUSES = {"NOT_RUN", "IN_PROGRESS", "PASS", "FAIL", "BLOCKED"}
MANDATORY_GATE_SEAL_KINDS = {"TESTS_VERIFIED", "EVIDENCE_VERIFIED"}
COMMIT_PATTERN = re.compile(r"^([a-f0-9]{40}|[a-f0-9]{64})$")
LOCK_TIMEOUT_SECONDS = 10


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--state", type=Path, default=DEFAULT_STATE)
    result.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    result.add_argument("--expected-revision", type=int, required=True)
    result.add_argument("--phase", choices=sorted(PHASES), required=True)
    result.add_argument("--next-action", required=True)
    result.add_argument("--step", action="append", default=[], help="Completed step to append; may be repeated")
    result.add_argument("--work-package-id")
    result.add_argument("--owner")
    result.add_argument("--input-snapshot-ref")
    result.add_argument("--evidence-ref", action="append")
    result.add_argument("--pending-finding", action="append")
    result.add_argument("--resolve-finding", action="append")
    result.add_argument("--owned-file", action="append")
    result.add_argument("--seal-index", type=Path, default=DEFAULT_SEAL_INDEX)
    result.add_argument("--seal-root", type=Path, default=DEFAULT_SEAL_ROOT)
    result.add_argument("--slice", dest="slice_id", help="Slice targeted by slice options when no --gate is given")
    result.add_argument("--gate", action="append", default=[], metavar="GATE=STATUS")
    result.add_argument("--gate-seal", action="append", default=[], metavar="GATE=SEAL_ID",
                        help="Attach an indexed seal record to a gate; may be repeated")
    result.add_argument("--slice-commit", help="Commit identifier of the tested tree for the slice")
    result.add_argument("--slice-evidence-ref", action="append", default=[])
    result.add_argument("--slice-blocker", action="append", default=[])
    result.add_argument("--resolve-blocker", action="append", default=[])
    return result


@contextmanager
def exclusive_lock(state_path):
    lock_path = state_path.with_name(state_path.name + ".execution.lock")
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise ValueError(f"Timed out waiting for advisory lock: {lock_path}")
                time.sleep(0.05)
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def write_atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    old_mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        os.fchmod(fd, old_mode)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
        fsync_directory(path.parent)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def fsync_directory(path):
    dir_fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def state_bytes(state):
    return (json.dumps(state, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def read_state(path):
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read state JSON: {exc}") from exc
    if not isinstance(state, dict):
        raise ValueError("Canonical state JSON must be an object")
    revision = state.get("revision")
    if isinstance(revision, bool) or not isinstance(revision, int):
        raise ValueError("Canonical state revision must be an integer")
    if not isinstance(state.get("active_work"), dict):
        raise ValueError("Canonical state active_work must be an object")
    return state


def read_ledger(path):
    if not path.exists():
        return []
    raw = path.read_bytes()
    if raw and not raw.endswith(b"\n"):
        raise ValueError("Execution ledger has an incomplete final JSONL record")
    rows = []
    previous_hash = ""
    for line_number, line in enumerate(raw.splitlines(), start=1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Execution ledger JSON error on line {line_number}: {exc}") from exc
        event_hash = row.get("event_hash")
        event = {key: value for key, value in row.items() if key != "event_hash"}
        if row.get("previous_hash") != previous_hash or event_hash != digest(event):
            raise ValueError(f"Execution ledger hash-chain validation failed on line {line_number}")
        if not isinstance(row.get("revision"), int):
            raise ValueError(f"Execution ledger revision is invalid on line {line_number}")
        rows.append(row)
        previous_hash = event_hash
    if any(right["revision"] != left["revision"] + 1 for left, right in zip(rows, rows[1:])):
        raise ValueError("Execution ledger has a revision gap; revisions must be contiguous after the first anchor")
    return rows


def read_journal(path):
    if not path.exists():
        return []
    events = []
    for event_path in sorted(path.glob("event-*.json")):
        try:
            prepared = json.loads(event_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Cannot read prepared journal event {event_path.name}: {exc}") from exc
        event = prepared.get("event")
        after = prepared.get("state_after")
        if not isinstance(event, dict) or not isinstance(after, dict):
            raise ValueError(f"Malformed prepared journal event: {event_path.name}")
        if prepared.get("event_hash") != digest(event) or event.get("state_sha256") != digest(after):
            raise ValueError(f"Prepared journal event hash validation failed: {event_path.name}")
        if event_path.name != f"event-{event.get('revision', -1):010d}.json":
            raise ValueError(f"Prepared journal event filename/revision mismatch: {event_path.name}")
        events.append(prepared)
    if any(left["event"]["revision"] >= right["event"]["revision"] for left, right in zip(events, events[1:])):
        raise ValueError("Prepared journal revisions are not strictly increasing")
    return events


def append_ledger(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o600)
    with os.fdopen(fd, "ab") as stream:
        stream.write(canonical_bytes(row) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    fsync_directory(path.parent)


def recover_prepared_event(state, prepared, by_revision, previous_hash, state_path, ledger_path):
    event = prepared["event"]
    revision = event["revision"]
    existing = by_revision.get(revision)
    if existing:
        if existing.get("event_hash") != prepared["event_hash"]:
            raise ValueError(f"Journal/ledger conflict at revision {revision}")
        if state.get("revision") == revision and digest(state) != event.get("state_sha256"):
            raise ValueError(f"Canonical state hash disagrees with committed event at revision {revision}")
        return state, None, False
    if event.get("previous_hash") != previous_hash:
        raise ValueError(f"Journal hash-chain predecessor mismatch at revision {revision}")
    current_revision = state.get("revision")
    if current_revision == revision - 1 and digest(state) == event.get("state_before_sha256"):
        state = prepared["state_after"]
        write_atomic(state_path, state_bytes(state))
    elif current_revision != revision or digest(state) != event.get("state_sha256"):
        raise ValueError(f"Cannot recover prepared event at revision {revision}: canonical state diverged")
    row = {**event, "event_hash": prepared["event_hash"]}
    append_ledger(ledger_path, row)
    return state, row, True


def recover(state_path, ledger_path):
    state = read_state(state_path)
    rows = read_ledger(ledger_path)
    events = read_journal(ledger_path.with_name("execution_journal"))
    by_revision = {row["revision"]: row for row in rows}
    recovered = False
    previous_hash = rows[-1]["event_hash"] if rows else ""
    for prepared in events:
        state, row, did_recover = recover_prepared_event(
            state, prepared, by_revision, previous_hash, state_path, ledger_path
        )
        if row is not None:
            rows.append(row)
            by_revision[row["revision"]] = row
            previous_hash = row["event_hash"]
        recovered = recovered or did_recover
    if rows:
        latest = rows[-1]
        if state.get("revision") != latest.get("revision"):
            raise ValueError(
                f"Canonical state revision {state.get('revision')} does not match latest ledger revision {latest.get('revision')}"
            )
        if digest(state) != latest.get("state_sha256"):
            raise ValueError(f"Canonical state hash disagrees with latest ledger revision {latest.get('revision')}")
    if recovered:
        return state, True
    return state, False


def validate_active_work_patch(patch):
    allowed = {
        "work_package_id", "owner", "input_snapshot_ref", "evidence_refs", "pending_findings", "owned_files",
        "resolve_findings",
    }
    unknown = set(patch) - allowed
    if unknown:
        raise ValueError(f"Unsupported active_work patch field(s): {', '.join(sorted(unknown))}")
    for key in ("work_package_id", "owner", "input_snapshot_ref"):
        if key in patch:
            if not isinstance(patch[key], str) or not patch[key].strip():
                raise ValueError(f"active_work.{key} must be a non-empty string")
    for key in ("evidence_refs", "pending_findings", "resolve_findings", "owned_files"):
        if key in patch:
            if any(not isinstance(item, str) or not item.strip() for item in patch[key]):
                raise ValueError(f"active_work.{key} entries must be non-empty strings")


def append_active_work_entries(active, field, entries):
    existing = active.setdefault(field, [])
    if not isinstance(existing, list):
        raise ValueError(f"active_work.{field} must be an array")
    existing.extend(entries)


def resolve_pending_findings(active, findings):
    pending = active.setdefault("pending_findings", [])
    if not isinstance(pending, list):
        raise ValueError("active_work.pending_findings must be an array")
    for finding in findings:
        if finding not in pending:
            raise ValueError(f"Cannot resolve untracked pending finding: {finding}")
        pending.remove(finding)


def apply_active_work_patch(active, patch):
    for key in ("work_package_id", "owner", "input_snapshot_ref"):
        if key in patch:
            active[key] = patch[key]
    for key in ("evidence_refs", "pending_findings"):
        if key in patch:
            append_active_work_entries(active, key, patch[key])
    if "owned_files" in patch:
        active["owned_files"] = patch["owned_files"]
    if "resolve_findings" in patch:
        resolve_pending_findings(active, patch["resolve_findings"])


def validate_phase_authority(state, phase):
    if phase not in IMPLEMENTATION_PHASES:
        return
    mode = state.get("work_mode")
    if mode not in WORK_MODES:
        raise ValueError(f"Implementation phase requires a supported work_mode; found {mode!r}")
    if mode == "SPECIFICATION_ONLY":
        raise ValueError(f"SPECIFICATION_ONLY mode cannot advance active_work to phase {phase}")
    if "execution_authorized" in state and state["execution_authorized"] is not True:
        raise ValueError("Implementation phase requires execution_authorized=true")


def slice_index_for_task(work_package_id, slices):
    matches = [index for index, name in enumerate(slices) if work_package_id == name or work_package_id.startswith(f"{name}-")]
    if len(matches) != 1:
        raise ValueError(f"active_work work package does not identify one known slice: {work_package_id!r}")
    return matches[0]


def slice_ceiling(state):
    """Return (sorted slice names, index of the latest slice that may be worked on)."""
    slices = state.get("slices")
    if not isinstance(slices, dict) or not slices:
        raise ValueError("Canonical state must contain non-empty slice authority")
    names = sorted(slices)
    current_slice = state.get("current_slice")
    if current_slice not in slices:
        raise ValueError("Canonical current_slice must identify a configured slice")
    earliest_incomplete = len(names)
    for index, name in enumerate(names):
        item = slices[name]
        gates = item.get("gates", {})
        if item.get("status") != "PASS" or not gates or any(status != "PASS" for status in gates.values()):
            earliest_incomplete = index
            break
    return names, min(names.index(current_slice), earliest_incomplete)


def validate_active_work_scope(state, patch):
    names, ceiling = slice_ceiling(state)
    active = state.get("active_work")
    if not isinstance(active, dict):
        raise ValueError("Canonical state must contain an active_work object")
    task_id = patch.get("work_package_id", active.get("work_package_id", ""))
    task_index = slice_index_for_task(task_id, names)
    if task_index > ceiling:
        raise ValueError(f"active_work task slice {names[task_index]} is beyond current/earliest incomplete slice {names[ceiling]}")


def split_pair(value, shape):
    left, separator, right = value.partition("=")
    if not separator or not left.strip() or not right.strip():
        raise ValueError(f"Expected {shape}, found {value!r}")
    return left.strip(), right.strip()


def build_slice_request(slice_id, gates, gate_seals, commit, evidence_refs, blockers, resolve_blockers):
    """Parse slice options into a request; return None when no slice option was given."""
    request = {"gates": {}, "gate_seals": {}}
    for value in gates:
        gate, status = split_pair(value, "GATE=STATUS")
        if status not in GATE_STATUSES:
            raise ValueError(f"Unsupported gate status {status!r} for {gate}")
        if gate in request["gates"]:
            raise ValueError(f"Duplicate gate option: {gate}")
        request["gates"][gate] = status
    for value in gate_seals:
        gate, seal_id = split_pair(value, "GATE=SEAL_ID")
        seal_ids = request["gate_seals"].setdefault(gate, [])
        if seal_id not in seal_ids:
            seal_ids.append(seal_id)
    for key, entries in (("evidence_refs", evidence_refs), ("blockers", blockers), ("resolve_blockers", resolve_blockers)):
        if any(not isinstance(item, str) or not item.strip() for item in entries):
            raise ValueError(f"Slice {key} entries must be non-empty strings")
        if entries:
            request[key] = list(entries)
    if commit is not None:
        if not COMMIT_PATTERN.match(commit):
            raise ValueError("Slice commit must be a 40- or 64-character lowercase hexadecimal identifier")
        request["commit"] = commit
    if slice_id is not None:
        request["slice_id"] = slice_id
    has_options = bool(request["gates"] or request["gate_seals"] or len(request) > 2)
    if not has_options:
        return None
    if not request["gates"] and not request["gate_seals"] and "slice_id" not in request:
        raise ValueError("Slice options require --gate or --slice")
    return request


def target_slice(state, request):
    names, ceiling = slice_ceiling(state)
    slices = state["slices"]
    requested = request.get("slice_id")
    if requested is not None and requested not in slices:
        raise ValueError(f"Unknown slice: {requested}")
    owners = set() if requested is None else {requested}
    for gate in [*request["gates"], *request["gate_seals"]]:
        matches = [name for name in names if gate in slices[name].get("gates", {})]
        if len(matches) != 1:
            raise ValueError(f"Unknown gate: {gate}")
        owners.add(matches[0])
    if len(owners) != 1:
        raise ValueError("Gate and slice options must identify one slice")
    slice_id = owners.pop()
    if names.index(slice_id) > ceiling:
        raise ValueError(f"Slice patch targets {slice_id}, beyond current/earliest incomplete slice {names[ceiling]}")
    return slice_id


def read_seal_index(seal_index):
    try:
        index = json.loads(Path(seal_index).read_text(encoding="utf-8"))
        records = index["records"]
        by_id = {record["seal_id"]: record for record in records}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ValueError(f"Seal index is missing or unreadable: {seal_index}") from exc
    if len(by_id) != len(records):
        raise ValueError("Duplicate seal identity in seal index")
    return by_id


def resolve_seal(seal_id, gate, slice_id, by_id, seal_root):
    """Return (state reference, verdict) for one indexed, hash-verified seal record."""
    if seal_id not in by_id:
        raise ValueError(f"Seal not in canonical index: {seal_id}")
    indexed = by_id[seal_id]
    root = Path(seal_root).resolve()
    path = (root / str(indexed.get("path", ""))).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Seal path escapes the seal root: {seal_id}")
    if not path.is_file():
        raise ValueError(f"Missing seal record: {seal_id}")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != indexed.get("record_sha256"):
        raise ValueError(f"Seal record changed: {seal_id}")
    try:
        record = json.loads(data.decode("utf-8"))
        identity = (record["seal_id"], record["kind"])
        scope_ids = list(record["scope_ids"])
        verdict = record["verdict"]
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError(f"Seal record is not a valid seal: {seal_id}") from exc
    if identity != (seal_id, indexed.get("kind")):
        raise ValueError(f"Seal index and record disagree: {seal_id}")
    scope_id = gate if gate in scope_ids else slice_id if slice_id in scope_ids else None
    if scope_id is None:
        raise ValueError(f"Seal scope does not cover {gate} or {slice_id}: {seal_id}")
    reference = {"seal_id": seal_id, "path": indexed["path"], "record_sha256": indexed["record_sha256"],
                 "kind": indexed["kind"], "scope_id": scope_id}
    return reference, verdict


def resolve_slice_patch(state, request, seal_index, seal_root):
    """Validate a slice request against state and seals; return the patch recorded in the event."""
    slice_id = target_slice(state, request)
    item = state["slices"][slice_id]
    patch = {"slice_id": slice_id}
    if request["gates"]:
        patch["gates"] = dict(request["gates"])
    by_id = read_seal_index(seal_index) if request["gate_seals"] else {}
    verdicts = {}
    new_refs = {}
    superseded = {}
    for gate, seal_ids in request["gate_seals"].items():
        existing = {ref["seal_id"]: ref for ref in item.get("gate_seal_refs", {}).get(gate, [])}
        for seal_id in seal_ids:
            reference, verdict = resolve_seal(seal_id, gate, slice_id, by_id, seal_root)
            verdicts[(gate, seal_id)] = verdict
            replaced = by_id[seal_id].get("supersedes")
            if replaced in existing and replaced not in superseded.get(gate, []):
                superseded.setdefault(gate, []).append(replaced)
            if seal_id in existing:
                if existing[seal_id] != reference:
                    raise ValueError(f"Seal reference conflict for {gate}: {seal_id}")
                continue
            new_refs.setdefault(gate, []).append(reference)
    if new_refs:
        patch["gate_seal_refs"] = new_refs
    if superseded:
        patch["superseded_seal_refs"] = superseded
    for key in ("commit", "evidence_refs", "blockers", "resolve_blockers"):
        if key in request:
            patch[key] = request[key]
    for blocker in patch.get("resolve_blockers", []):
        if blocker not in item.get("blockers", []):
            raise ValueError(f"Cannot resolve untracked blocker: {blocker}")
    for gate, status in request["gates"].items():
        if status != "PASS":
            continue
        if any(verdict != "PASS" for (seal_gate, _), verdict in verdicts.items() if seal_gate == gate):
            raise ValueError(f"Nonpassing seal used for PASS gate {gate}")
        kept = [ref for ref in item.get("gate_seal_refs", {}).get(gate, [])
                if ref["seal_id"] not in superseded.get(gate, [])]
        references = [*kept, *new_refs.get(gate, [])]
        if not MANDATORY_GATE_SEAL_KINDS <= {ref["kind"] for ref in references}:
            raise ValueError(f"PASS gate {gate} requires TESTS_VERIFIED and EVIDENCE_VERIFIED seal references")
        if not (patch.get("commit") or item.get("commit")):
            raise ValueError(f"PASS gate {gate} requires a slice commit")
    return patch


def apply_slice_patch(state, patch):
    item = state["slices"][patch["slice_id"]]
    item["gates"].update(patch.get("gates", {}))
    for gate, seal_ids in patch.get("superseded_seal_refs", {}).items():
        current = item.setdefault("gate_seal_refs", {}).setdefault(gate, [])
        current[:] = [ref for ref in current if ref["seal_id"] not in seal_ids]
    for gate, references in patch.get("gate_seal_refs", {}).items():
        item.setdefault("gate_seal_refs", {}).setdefault(gate, []).extend(references)
    if "commit" in patch:
        item["commit"] = patch["commit"]
    item.setdefault("evidence_refs", []).extend(patch.get("evidence_refs", []))
    blockers = item.setdefault("blockers", [])
    for blocker in patch.get("resolve_blockers", []):
        blockers.remove(blocker)
    blockers.extend(patch.get("blockers", []))


def update_active_work(state, phase, next_action, steps, patch):
    active = state.get("active_work")
    if not isinstance(active, dict):
        raise ValueError("Canonical state must contain an active_work object")
    completed = active.get("completed_steps")
    if not isinstance(completed, list):
        raise ValueError("active_work.completed_steps must be an array")
    validate_active_work_patch(patch)
    active["phase"] = phase
    active["next_action"] = next_action
    active["completed_steps"].extend(steps)
    apply_active_work_patch(active, patch)


def prepare_event(state, expected_revision, phase, next_action, steps, previous_hash, patch=None,
                  slice_request=None, seal_index=DEFAULT_SEAL_INDEX, seal_root=DEFAULT_SEAL_ROOT):
    if state.get("revision") != expected_revision:
        raise ValueError(f"Revision conflict: expected {expected_revision}, found {state.get('revision')}")
    patch = patch or {}
    validate_phase_authority(state, phase)
    validate_active_work_scope(state, patch)
    slice_patch = None
    if slice_request is not None:
        slice_patch = resolve_slice_patch(state, slice_request, seal_index, seal_root)
    before_hash = digest(state)
    updated = json.loads(json.dumps(state))
    update_active_work(updated, phase, next_action, steps, patch)
    if slice_patch is not None:
        apply_slice_patch(updated, slice_patch)
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    updated["revision"] = expected_revision + 1
    if "last_updated_at" in updated:
        updated["last_updated_at"] = timestamp
    event = {
        "revision": expected_revision + 1,
        "previous_hash": previous_hash,
        "state_before_sha256": before_hash,
        "state_sha256": digest(updated),
        "phase": phase,
        "next_action": next_action,
        "steps": steps,
        "active_work_patch": patch,
        "timestamp": timestamp,
    }
    if slice_patch is not None:
        event["slice_patch"] = slice_patch
    return {"event": event, "state_after": updated, "event_hash": digest(event)}


def update(state_path, ledger_path, expected_revision, phase, next_action, steps, patch=None,
           slice_request=None, seal_index=DEFAULT_SEAL_INDEX, seal_root=DEFAULT_SEAL_ROOT):
    with exclusive_lock(state_path):
        state, recovered = recover(state_path, ledger_path)
        if recovered:
            raise ValueError(f"Recovered pending checkpoint at revision {state.get('revision')}; re-read state before updating")
        if state.get("revision") != expected_revision:
            raise ValueError(f"Revision conflict: expected {expected_revision}, found {state.get('revision')}")
        rows = read_ledger(ledger_path)
        previous_hash = rows[-1]["event_hash"] if rows else ""
        prepared = prepare_event(state, expected_revision, phase, next_action, steps, previous_hash, patch,
                                 slice_request, seal_index, seal_root)
        journal_dir = ledger_path.with_name("execution_journal")
        journal_dir.mkdir(parents=True, exist_ok=True)
        fsync_directory(journal_dir.parent)
        journal_path = journal_dir / f"event-{expected_revision + 1:010d}.json"
        if journal_path.exists():
            raise ValueError(f"Prepared journal event already exists: {journal_path}")
        write_atomic(journal_path, (json.dumps(prepared, sort_keys=True, indent=2) + "\n").encode("utf-8"))
        write_atomic(state_path, state_bytes(prepared["state_after"]))
        row = {**prepared["event"], "event_hash": prepared["event_hash"]}
        append_ledger(ledger_path, row)
        return expected_revision + 1


def main(argv=None):
    args = parser().parse_args(argv)
    if not args.next_action.strip():
        print("State update rejected: --next-action must not be empty", file=sys.stderr)
        return 2
    if not args.state.is_file():
        print(f"State file does not exist: {args.state}", file=sys.stderr)
        return 2
    patch = {}
    for key in ("work_package_id", "owner", "input_snapshot_ref"):
        value = getattr(args, key)
        if value is not None:
            patch[key] = value
    for argument, key in (("evidence_ref", "evidence_refs"), ("pending_finding", "pending_findings"), ("owned_file", "owned_files")):
        value = getattr(args, argument)
        if value is not None:
            patch[key] = value
    if args.resolve_finding is not None:
        patch["resolve_findings"] = args.resolve_finding
    try:
        slice_request = build_slice_request(args.slice_id, args.gate, args.gate_seal, args.slice_commit,
                                            args.slice_evidence_ref, args.slice_blocker, args.resolve_blocker)
        revision = update(args.state, args.ledger, args.expected_revision, args.phase, args.next_action, args.step,
                          patch, slice_request, args.seal_index, args.seal_root)
    except OSError as exc:
        diagnostic = {
            "status": "CHECKPOINT_PENDING",
            "failure_class": "IO_OR_FSYNC_ERROR",
            "message": str(exc),
            "state_path": str(args.state),
            "ledger_path": str(args.ledger),
            "expected_revision": args.expected_revision,
            "platform_limitation": "Filesystem IO/fsync durability was not confirmed; this run does not claim a successful save.",
            "recovery_next_action": (
                f"Inspect {args.state} and {args.ledger.with_name('execution_journal')}; "
                f"rerun the same checkpoint with --expected-revision {args.expected_revision} if state remains at that revision; "
                f"if state advanced to {args.expected_revision + 1}, let recovery reconcile that event before starting another update."
            ),
        }
        print(json.dumps(diagnostic, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 2
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"Checkpoint rejected: {exc}", file=sys.stderr)
        return 2
    print(f"Execution checkpoint saved at revision {revision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
