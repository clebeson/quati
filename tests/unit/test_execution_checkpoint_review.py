"""Independent regression checks for checkpoint durability and authority limits."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "checkpoint_execution.py"
SPEC = importlib.util.spec_from_file_location("checkpoint_execution_review", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
checkpoint = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checkpoint)


def make_state(path: Path) -> dict:
    state = {
        "revision": 8,
        "work_mode": "IMPLEMENTATION_AUTHORIZED",
        "current_slice": "S00",
        "slices": {
            "S00": {"status": "IN_PROGRESS", "gates": {"GATE-1": "NOT_RUN"}},
            **{
                f"S{index:02d}": {
                    "status": "NOT_STARTED",
                    "gates": {"GATE-1": "NOT_RUN"},
                }
                for index in range(1, 8)
            },
        },
        "active_work": {
            "work_package_id": "S00-T01",
            "phase": "TDD_RED",
            "completed_steps": ["read contract"],
            "next_action": "implement after red tests",
        },
    }
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return state


def test_parent_directory_is_synced_before_canonical_state_replace(tmp_path, monkeypatch):
    """A fresh journal directory entry must be durable before state can advance."""
    state_path = tmp_path / "implementation_state.json"
    ledger_path = tmp_path / "execution_ledger.jsonl"
    make_state(state_path)
    events: list[tuple[str, Path]] = []
    real_replace = checkpoint.os.replace
    real_fsync_directory = checkpoint.fsync_directory

    def record_replace(source, destination):
        events.append(("replace", Path(destination)))
        return real_replace(source, destination)

    def record_directory_fsync(path):
        events.append(("fsync_directory", Path(path)))
        return real_fsync_directory(path)

    monkeypatch.setattr(checkpoint.os, "replace", record_replace)
    monkeypatch.setattr(checkpoint, "fsync_directory", record_directory_fsync)

    checkpoint.update(
        state_path,
        ledger_path,
        expected_revision=8,
        phase="AUDIT",
        next_action="review durability",
        steps=["audit checkpoint helper"],
    )

    state_replace = events.index(("replace", state_path))
    assert any(
        kind == "fsync_directory" and path == tmp_path
        for kind, path in events[:state_replace]
    ), "journal parent must be synced before replacing canonical state"


def test_metadata_cli_cannot_change_work_mode_or_gate_status(tmp_path):
    """A CLI metadata patch preserves authority fields; unknown fields are rejected."""
    state_path = tmp_path / "state.json"
    ledger_path = tmp_path / "execution_ledger.jsonl"
    initial = make_state(state_path)

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--state",
            str(state_path),
            "--ledger",
            str(ledger_path),
            "--expected-revision",
            "8",
            "--phase",
            "AUDIT",
            "--next-action",
            "record evidence metadata",
            "--owner",
            "reviewer",
            "--work-mode",
            "SPECIFICATION_ONLY",
            "--gate",
            "S00=PASS",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    after = json.loads(state_path.read_text(encoding="utf-8"))
    assert after == initial
    assert not ledger_path.exists()


@pytest.mark.parametrize("slice_authority", ["missing", "empty", "no_current", "unknown_current"])
def test_implementation_update_fails_closed_without_slice_authority(tmp_path, slice_authority):
    """Missing/invalid slice authority cannot disable the active-slice ceiling."""
    state_path = tmp_path / f"{slice_authority}.json"
    ledger_path = tmp_path / f"{slice_authority}.jsonl"
    state = make_state(state_path)
    if slice_authority == "missing":
        state.pop("slices")
    elif slice_authority == "empty":
        state["slices"] = {}
    elif slice_authority == "no_current":
        state.pop("current_slice")
    else:
        state["current_slice"] = "S99"
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    before = state_path.read_bytes()

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--state", str(state_path),
            "--ledger", str(ledger_path),
            "--expected-revision", "8",
            "--phase", "IMPLEMENT",
            "--next-action", "must fail closed",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert state_path.read_bytes() == before
    assert not ledger_path.exists()


def test_valid_hash_chain_cannot_skip_a_committed_revision(tmp_path):
    """Hash-valid rows must still advance by exactly one after the initial anchor."""
    state_path = tmp_path / "state.json"
    ledger_path = tmp_path / "execution_ledger.jsonl"
    make_state(state_path)
    checkpoint.update(
        state_path,
        ledger_path,
        expected_revision=8,
        phase="TDD_RED",
        next_action="implement",
        steps=["red test"],
    )
    rows = checkpoint.read_ledger(ledger_path)
    after_revision_nine = json.loads(state_path.read_text(encoding="utf-8"))

    # Simulate a missing revision 10 while constructing a self-consistent,
    # hash-valid event 11 that points directly to the event at revision 9.
    before_revision_eleven = json.loads(json.dumps(after_revision_nine))
    before_revision_eleven["revision"] = 10
    prepared = checkpoint.prepare_event(
        before_revision_eleven,
        expected_revision=10,
        phase="AUDIT",
        next_action="resume",
        steps=[],
        previous_hash=rows[-1]["event_hash"],
    )
    journal_dir = ledger_path.with_name("execution_journal")
    journal_dir.mkdir(exist_ok=True)
    journal_path = journal_dir / "event-0000000011.json"
    journal_path.write_text(json.dumps(prepared), encoding="utf-8")
    state_path.write_bytes(checkpoint.state_bytes(prepared["state_after"]))
    checkpoint.append_ledger(
        ledger_path,
        {**prepared["event"], "event_hash": prepared["event_hash"]},
    )

    with pytest.raises(ValueError, match="revision|contiguous|gap"):
        checkpoint.recover(state_path, ledger_path)


def test_two_cli_writers_with_same_revision_have_one_winner(tmp_path):
    """Concurrent real CLI writers serialize; exactly one can commit revision 9."""
    state_path = tmp_path / "state.json"
    ledger_path = tmp_path / "execution_ledger.jsonl"
    make_state(state_path)
    go_path = tmp_path / "go"
    ready_paths = [tmp_path / "ready-0", tmp_path / "ready-1"]
    gate_code = (
        "import os,sys,time\n"
        "helper,ready,go,*args=sys.argv[1:]\n"
        "open(ready,'wb').close()\n"
        "deadline=time.monotonic()+10\n"
        "while not os.path.exists(go):\n"
        "  if time.monotonic()>deadline: raise SystemExit(90)\n"
        "  time.sleep(.001)\n"
        "os.execv(sys.executable,[sys.executable,helper,*args])\n"
    )
    cli_args = [
        "--state", str(state_path),
        "--ledger", str(ledger_path),
        "--expected-revision", "8",
        "--phase", "AUDIT",
        "--next-action", "concurrent checkpoint",
    ]
    processes = [
        subprocess.Popen(
            [
                sys.executable,
                "-c",
                gate_code,
                str(SCRIPT),
                str(ready_paths[index]),
                str(go_path),
                *cli_args,
            ],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for index in range(2)
    ]
    try:
        deadline = time.monotonic() + 10
        while not all(path.exists() for path in ready_paths):
            if time.monotonic() >= deadline:
                pytest.fail("concurrent CLI writers did not reach the start barrier")
            time.sleep(.005)
        go_path.touch()
        results = [process.communicate(timeout=15) for process in processes]
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.wait()

    return_codes = [process.returncode for process in processes]
    assert return_codes.count(0) == 1, results
    assert return_codes.count(2) == 1, results
    assert any("Revision conflict" in stderr for _, stderr in results)
    final_state = json.loads(state_path.read_text(encoding="utf-8"))
    assert final_state["revision"] == 9
    assert final_state["active_work"]["next_action"] == "concurrent checkpoint"
    rows = checkpoint.read_ledger(ledger_path)
    assert len(rows) == 1
    assert rows[0]["revision"] == 9
    assert checkpoint.digest(final_state) == rows[0]["state_sha256"]


@pytest.mark.parametrize(
    ("crash_point", "expected_state_revision_before_recovery"),
    [("journal", 8), ("state", 9)],
)
def test_sigkill_at_commit_boundaries_recovers_through_normal_cli(
    tmp_path, crash_point, expected_state_revision_before_recovery
):
    """SIGKILL after journal or state write is reconciled by the public helper CLI."""
    state_path = tmp_path / "state.json"
    ledger_path = tmp_path / "execution_ledger.jsonl"
    make_state(state_path)
    target_path = (
        ledger_path.with_name("execution_journal") / "event-0000000009.json"
        if crash_point == "journal"
        else state_path
    )
    wrapper_code = (
        "import os,signal,sys\n"
        f"sys.path.insert(0,{str(SCRIPT.parent)!r})\n"
        "import checkpoint_execution as checkpoint\n"
        "from pathlib import Path\n"
        "target=Path(sys.argv[1])\n"
        "args=sys.argv[2:]\n"
        "write=checkpoint.write_atomic\n"
        "def crash_after_target(path,data):\n"
        "  write(path,data)\n"
        "  if Path(path)==target: os.kill(os.getpid(),signal.SIGKILL)\n"
        "checkpoint.write_atomic=crash_after_target\n"
        "raise SystemExit(checkpoint.main(args))\n"
    )
    interrupted = subprocess.run(
        [
            sys.executable,
            "-c",
            wrapper_code,
            str(target_path),
            "--state", str(state_path),
            "--ledger", str(ledger_path),
            "--expected-revision", "8",
            "--phase", "AUDIT",
            "--next-action", f"recover after {crash_point}",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert interrupted.returncode == -signal.SIGKILL
    before_recovery = json.loads(state_path.read_text(encoding="utf-8"))
    assert before_recovery["revision"] == expected_state_revision_before_recovery
    assert not ledger_path.exists()

    recovery = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--state", str(state_path),
            "--ledger", str(ledger_path),
            "--expected-revision", "8",
            "--phase", "AUDIT",
            "--next-action", "must re-read recovered revision",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert recovery.returncode != 0
    assert "Recovered pending checkpoint at revision 9" in recovery.stderr
    recovered_state = json.loads(state_path.read_text(encoding="utf-8"))
    assert recovered_state["revision"] == 9
    assert recovered_state["active_work"]["next_action"] == f"recover after {crash_point}"
    rows = checkpoint.read_ledger(ledger_path)
    assert len(rows) == 1
    assert rows[0]["revision"] == 9
    assert checkpoint.digest(recovered_state) == rows[0]["state_sha256"]
