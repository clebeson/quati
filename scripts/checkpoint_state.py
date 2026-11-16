#!/usr/bin/env python3
"""Legacy CAS state updater for unjournaled state files only.

It refuses any state file that has an execution ledger or journal beside it, because
writing such state without the journal would desynchronize checkpoint_execution.py.
"""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

VALID_STATUSES = {"NOT_STARTED", "IN_PROGRESS", "PASS", "FAIL", "BLOCKED"}
VALID_GATE_STATUSES = VALID_STATUSES | {"NOT_RUN"}
JOURNAL_ARTIFACTS = ("execution_ledger.jsonl", "execution_journal")
DEFAULT_STATE = Path(__file__).resolve().parents[1] / "docs/implementation/implementation_state.json"


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--state", type=Path, default=DEFAULT_STATE)
    result.add_argument("--expected-revision", type=int, required=True)
    result.add_argument("--slice", dest="slice_id", help="Slice whose status or gates are being updated")
    result.add_argument("--status", choices=sorted(VALID_STATUSES))
    result.add_argument("--gate", action="append", default=[], metavar="GATE=STATUS")
    result.add_argument("--evidence-ref", action="append", default=[])
    result.add_argument("--blocker", action="append", default=[])
    result.add_argument("--commit", help="Implementation commit identifier, if applicable")
    result.add_argument("--advance-to", metavar="SLICE", help="Set current_slice, provided no earlier slice is incomplete")
    return result


def gate_updates(items):
    updates = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"Invalid gate update {item!r}; expected GATE=STATUS")
        key, value = item.split("=", 1)
        if value not in VALID_GATE_STATUSES:
            raise ValueError(f"Invalid gate status {value!r}")
        if key in updates:
            raise ValueError(f"Gate {key} was supplied more than once")
        updates[key] = value
    return updates


def write_locked(path, args, updates):
    lock_path = path.with_name(path.name + ".lock")
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError(f"State is locked by another update: {lock_path}") from exc
    try:
        with os.fdopen(lock_fd, "w", encoding="utf-8") as lock_file:
            lock_file.write(f"pid={os.getpid()}\n")
            lock_file.flush()
            os.fsync(lock_file.fileno())
        state = json.loads(path.read_text(encoding="utf-8"))
        if state.get("revision") != args.expected_revision:
            raise ValueError(f"Revision conflict: expected {args.expected_revision}, found {state.get('revision')}")
        slices = state.get("slices", {})
        order = list(slices)
        sid = args.slice_id
        before_earliest = next((i for i, name in enumerate(order)
                                if slices[name].get("status") != "PASS" or not slices[name].get("gates")
                                or any(v != "PASS" for v in slices[name]["gates"].values())), len(order))
        if sid in slices and order.index(sid) > before_earliest:
            raise ValueError("Cannot modify a downstream slice while an earlier slice is incomplete")
        if sid and sid not in slices:
            raise ValueError(f"Unknown slice {sid}")
        if sid:
            gates = slices[sid].get("gates", {})
            unknown = set(updates) - set(gates)
            if unknown:
                raise ValueError(f"Unknown gate(s) for {sid}: {', '.join(sorted(unknown))}")
            gates.update(updates)
            if args.status:
                if args.status == "PASS" and any(value != "PASS" for value in gates.values()):
                    raise ValueError(f"Cannot mark {sid} PASS while one or more gates are not PASS")
                slices[sid]["status"] = args.status
            if args.evidence_ref:
                slices[sid].setdefault("evidence_refs", []).extend(args.evidence_ref)
            if args.blocker:
                slices[sid]["blockers"] = args.blocker
            if args.commit is not None:
                slices[sid]["commit"] = args.commit
        elif updates or args.status or args.evidence_ref or args.blocker or args.commit is not None:
            raise ValueError("--slice is required when updating slice details")

        for name, item in slices.items():
            if item.get("status") == "PASS" and (not item.get("gates") or any(v != "PASS" for v in item["gates"].values())):
                raise ValueError("PASS slice cannot retain incomplete gates")
        earliest = next((index for index, name in enumerate(order)
                         if slices[name].get("status") != "PASS" or not slices[name].get("gates") or any(status != "PASS" for status in slices[name].get("gates", {}).values())), len(order))
        if args.advance_to:
            if args.advance_to not in slices:
                raise ValueError(f"Unknown target slice {args.advance_to}")
            target = order.index(args.advance_to)
            if target > earliest:
                incomplete = order[earliest] if earliest < len(order) else "none"
                raise ValueError(f"Cannot advance past earliest incomplete slice {incomplete}")
            state["current_slice"] = args.advance_to
        elif sid and (state.get("current_slice") == sid or (sid in order and order.index(sid) == earliest)):
            state["current_slice"] = order[earliest] if earliest < len(order) else sid

        state["revision"] = args.expected_revision + 1
        state["last_updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        encoded = (json.dumps(state, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb") as tmp:
                tmp.write(encoded)
                tmp.flush()
                os.fsync(tmp.fileno())
            os.replace(tmp_name, path)
            dir_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
        return state["revision"]
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def main(argv=None):
    args = parser().parse_args(argv)
    if not args.state.is_file():
        print(f"State file does not exist: {args.state}", file=sys.stderr)
        return 2
    journaled = [name for name in JOURNAL_ARTIFACTS if (args.state.parent / name).exists()]
    if journaled:
        print(f"State update rejected: {args.state} is governed by {', '.join(journaled)}; "
              "use scripts/checkpoint_execution.py so the journal, ledger and state stay consistent.",
              file=sys.stderr)
        return 2
    try:
        revision = write_locked(args.state, args, gate_updates(args.gate))
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"State update rejected: {exc}", file=sys.stderr)
        return 2
    print(f"State updated at revision {revision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
