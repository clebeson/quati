#!/usr/bin/env python3
"""Record resumable active_work progress with revision CAS and a recoverable hash chain.

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


def validate_active_work_scope(state, patch):
    slices = state.get("slices")
    if not isinstance(slices, dict) or not slices:
        raise ValueError("Canonical state must contain non-empty slice authority")
    names = sorted(slices)
    current_slice = state.get("current_slice")
    if current_slice not in slices:
        raise ValueError("Canonical current_slice must identify a configured slice")
    active = state.get("active_work")
    if not isinstance(active, dict):
        raise ValueError("Canonical state must contain an active_work object")
    task_id = patch.get("work_package_id", active.get("work_package_id", ""))
    task_index = slice_index_for_task(task_id, names)
    earliest_incomplete = len(names)
    for index, name in enumerate(names):
        item = slices[name]
        gates = item.get("gates", {})
        if item.get("status") != "PASS" or not gates or any(status != "PASS" for status in gates.values()):
            earliest_incomplete = index
            break
    ceiling = min(names.index(current_slice), earliest_incomplete)
    if task_index > ceiling:
        raise ValueError(f"active_work task slice {names[task_index]} is beyond current/earliest incomplete slice {names[ceiling]}")


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


def prepare_event(state, expected_revision, phase, next_action, steps, previous_hash, patch=None):
    if state.get("revision") != expected_revision:
        raise ValueError(f"Revision conflict: expected {expected_revision}, found {state.get('revision')}")
    patch = patch or {}
    validate_phase_authority(state, phase)
    validate_active_work_scope(state, patch)
    before_hash = digest(state)
    updated = json.loads(json.dumps(state))
    update_active_work(updated, phase, next_action, steps, patch)
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
    return {"event": event, "state_after": updated, "event_hash": digest(event)}


def update(state_path, ledger_path, expected_revision, phase, next_action, steps, patch=None):
    with exclusive_lock(state_path):
        state, recovered = recover(state_path, ledger_path)
        if recovered:
            raise ValueError(f"Recovered pending checkpoint at revision {state.get('revision')}; re-read state before updating")
        if state.get("revision") != expected_revision:
            raise ValueError(f"Revision conflict: expected {expected_revision}, found {state.get('revision')}")
        rows = read_ledger(ledger_path)
        previous_hash = rows[-1]["event_hash"] if rows else ""
        prepared = prepare_event(state, expected_revision, phase, next_action, steps, previous_hash, patch)
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
        revision = update(args.state, args.ledger, args.expected_revision, args.phase, args.next_action, args.step, patch)
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
