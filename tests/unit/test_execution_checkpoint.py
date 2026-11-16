"""Public CLI coverage for resumable engineering progress checkpoints."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "checkpoint_execution.py"


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def cli(state, ledger, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--state", str(state), "--ledger", str(ledger), *map(str, args)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def state_fixture(path, work_mode="IMPLEMENTATION_AUTHORIZED", revision=4):
    state = {
        "revision": revision,
        "work_mode": work_mode,
        "current_slice": "S00",
        "slices": {
            "S00": {"status": "IN_PROGRESS", "gates": {"S00-GATE-01": "NOT_RUN"}},
            "S01": {"status": "NOT_STARTED", "gates": {"S01-GATE-01": "NOT_RUN"}},
        },
        "active_work": {
            "work_package_id": "S00-T01",
            "phase": "SDD",
            "completed_steps": ["read contract"],
            "next_action": "write tests",
        },
        "other": {"preserve": True},
    }
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return state


def test_revision_conflict_leaves_state_bytes_unchanged(tmp_path):
    state_path = tmp_path / "state.json"
    ledger_path = tmp_path / "execution_ledger.jsonl"
    state_fixture(state_path)
    before = state_path.read_bytes()

    result = cli(state_path, ledger_path, "--expected-revision", "3", "--phase", "IMPLEMENT",
                 "--next-action", "continue", "--step", "implemented guard")

    assert result.returncode != 0
    assert "Revision conflict" in result.stderr
    assert state_path.read_bytes() == before
    assert not ledger_path.exists()


def test_checkpoint_updates_active_work_and_appends_hash_chained_event(tmp_path):
    state_path = tmp_path / "state.json"
    ledger_path = tmp_path / "execution_ledger.jsonl"
    state_fixture(state_path)

    result = cli(state_path, ledger_path, "--expected-revision", "4", "--phase", "IMPLEMENT",
                 "--next-action", "inspect recovery path", "--step", "red test recorded",
                 "--step", "atomic update implemented")

    assert result.returncode == 0, result.stderr
    updated = json.loads(state_path.read_text(encoding="utf-8"))
    assert updated["revision"] == 5
    assert updated["active_work"]["phase"] == "IMPLEMENT"
    assert updated["active_work"]["next_action"] == "inspect recovery path"
    assert updated["active_work"]["completed_steps"] == ["read contract", "red test recorded", "atomic update implemented"]
    assert updated["other"] == {"preserve": True}
    rows = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["revision"] == 5
    assert rows[0]["previous_hash"] == ""
    event_hash = rows[0].pop("event_hash")
    assert event_hash == digest(rows[0])


def test_resume_applies_prepared_journal_event_and_completes_ledger(tmp_path):
    state_path = tmp_path / "state.json"
    ledger_path = tmp_path / "execution_ledger.jsonl"
    state = state_fixture(state_path)
    after = json.loads(json.dumps(state))
    after["revision"] = 5
    after["active_work"]["phase"] = "TDD_RED"
    after["active_work"]["next_action"] = "implement"
    after["active_work"]["completed_steps"].append("red tests recorded")
    event = {
        "revision": 5,
        "previous_hash": "",
        "state_before_sha256": digest(state),
        "state_sha256": digest(after),
        "phase": "TDD_RED",
        "next_action": "implement",
        "steps": ["red tests recorded"],
        "timestamp": "2026-11-15T00:00:00Z",
    }
    prepared = {"event": event, "state_after": after, "event_hash": digest(event)}
    journal = tmp_path / "execution_journal"
    journal.mkdir()
    (journal / "event-0000000005.json").write_text(json.dumps(prepared), encoding="utf-8")

    result = cli(state_path, ledger_path, "--expected-revision", "4", "--phase", "IMPLEMENT",
                 "--next-action", "finish implementation")

    assert result.returncode != 0
    assert "recovered" in result.stderr.lower()
    recovered = json.loads(state_path.read_text(encoding="utf-8"))
    assert recovered["revision"] == 5
    assert recovered["active_work"]["phase"] == "TDD_RED"
    rows = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["event_hash"] == prepared["event_hash"]


def test_resume_finishes_ledger_when_state_replace_was_already_durable(tmp_path):
    state_path = tmp_path / "state.json"
    ledger_path = tmp_path / "execution_ledger.jsonl"
    state = state_fixture(state_path)
    after = json.loads(json.dumps(state))
    after["revision"] = 5
    after["active_work"].update({"phase": "IMPLEMENT", "next_action": "resume", "completed_steps": ["read contract"]})
    event = {
        "revision": 5,
        "previous_hash": "",
        "state_before_sha256": digest(state),
        "state_sha256": digest(after),
        "phase": "IMPLEMENT",
        "next_action": "resume",
        "steps": [],
        "timestamp": "2026-11-15T00:00:00Z",
    }
    prepared = {"event": event, "state_after": after, "event_hash": digest(event)}
    journal = tmp_path / "execution_journal"
    journal.mkdir()
    (journal / "event-0000000005.json").write_text(json.dumps(prepared), encoding="utf-8")
    state_path.write_text(json.dumps(after, indent=2) + "\n", encoding="utf-8")

    result = cli(state_path, ledger_path, "--expected-revision", "5", "--phase", "EDD", "--next-action", "continue")

    assert result.returncode != 0
    assert "recovered" in result.stderr.lower()
    rows = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["event_hash"] == prepared["event_hash"]


def test_hash_chain_tampering_is_rejected_without_state_change(tmp_path):
    state_path = tmp_path / "state.json"
    ledger_path = tmp_path / "execution_ledger.jsonl"
    state_fixture(state_path)
    result = cli(state_path, ledger_path, "--expected-revision", "4", "--phase", "IMPLEMENT",
                 "--next-action", "first action")
    assert result.returncode == 0, result.stderr
    original_state = state_path.read_bytes()
    row = json.loads(ledger_path.read_text(encoding="utf-8"))
    row["next_action"] = "forged action"
    ledger_path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    result = cli(state_path, ledger_path, "--expected-revision", "5", "--phase", "EDD",
                 "--next-action", "continue")

    assert result.returncode != 0
    assert "hash" in result.stderr.lower()
    assert state_path.read_bytes() == original_state


def test_specification_only_rejects_implementation_phases(tmp_path):
    state_path = tmp_path / "state.json"
    ledger_path = tmp_path / "execution_ledger.jsonl"
    state_fixture(state_path, work_mode="SPECIFICATION_ONLY")
    before = state_path.read_bytes()

    result = cli(state_path, ledger_path, "--expected-revision", "4", "--phase", "IMPLEMENT",
                 "--next-action", "continue")

    assert result.returncode != 0
    assert "SPECIFICATION_ONLY" in result.stderr
    assert state_path.read_bytes() == before
    assert not ledger_path.exists()


def test_checkpoint_can_patch_only_active_work_metadata(tmp_path):
    state_path = tmp_path / "state.json"
    ledger_path = tmp_path / "execution_ledger.jsonl"
    state_fixture(state_path)

    result = cli(
        state_path,
        ledger_path,
        "--expected-revision", "4",
        "--phase", "AUDIT",
        "--next-action", "review findings",
        "--work-package-id", "S00-T02",
        "--owner", "Codex",
        "--input-snapshot-ref", "sha256:abc123",
        "--evidence-ref", "evidence/run-1.json",
        "--pending-finding", "one unresolved item",
        "--owned-file", "scripts/a.py",
        "--owned-file", "tests/a.py",
    )

    assert result.returncode == 0, result.stderr
    active = json.loads(state_path.read_text(encoding="utf-8"))["active_work"]
    assert active["work_package_id"] == "S00-T02"
    assert active["owner"] == "Codex"
    assert active["input_snapshot_ref"] == "sha256:abc123"
    assert active["evidence_refs"] == ["evidence/run-1.json"]
    assert active["pending_findings"] == ["one unresolved item"]
    assert active["owned_files"] == ["scripts/a.py", "tests/a.py"]


def test_first_ledger_event_can_anchor_at_existing_revision_eight(tmp_path):
    state_path = tmp_path / "state.json"
    ledger_path = tmp_path / "execution_ledger.jsonl"
    state_fixture(state_path, revision=8)

    result = cli(state_path, ledger_path, "--expected-revision", "8", "--phase", "AUDIT",
                 "--next-action", "review checkpoint")

    assert result.returncode == 0, result.stderr
    row = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert row["revision"] == 9


def test_missing_current_journal_and_mutated_state_are_rejected(tmp_path):
    state_path = tmp_path / "state.json"
    ledger_path = tmp_path / "execution_ledger.jsonl"
    state_fixture(state_path)
    result = cli(state_path, ledger_path, "--expected-revision", "4", "--phase", "IMPLEMENT",
                 "--next-action", "first action")
    assert result.returncode == 0, result.stderr
    (tmp_path / "execution_journal" / "event-0000000005.json").unlink()
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["active_work"]["next_action"] = "tampered"
    state_path.write_text(json.dumps(state), encoding="utf-8")

    result = cli(state_path, ledger_path, "--expected-revision", "5", "--phase", "AUDIT",
                 "--next-action", "continue")

    assert result.returncode != 0
    assert "state hash" in result.stderr.lower()


def test_unexplained_revision_gap_after_ledger_is_rejected(tmp_path):
    state_path = tmp_path / "state.json"
    ledger_path = tmp_path / "execution_ledger.jsonl"
    state_fixture(state_path)
    result = cli(state_path, ledger_path, "--expected-revision", "4", "--phase", "IMPLEMENT",
                 "--next-action", "first action")
    assert result.returncode == 0, result.stderr
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["revision"] = 6
    state_path.write_text(json.dumps(state), encoding="utf-8")

    result = cli(state_path, ledger_path, "--expected-revision", "6", "--phase", "AUDIT",
                 "--next-action", "continue")

    assert result.returncode != 0
    assert "revision" in result.stderr.lower()


def test_cli_adds_then_resolves_exact_pending_finding_and_records_patch(tmp_path):
    state_path = tmp_path / "state.json"
    ledger_path = tmp_path / "execution_ledger.jsonl"
    state_fixture(state_path)
    added = cli(state_path, ledger_path, "--expected-revision", "4", "--phase", "AUDIT",
                "--next-action", "investigate", "--pending-finding", "unresolved finding")
    assert added.returncode == 0, added.stderr
    resolving = cli(state_path, ledger_path, "--expected-revision", "5", "--phase", "AUDIT",
                    "--next-action", "close finding", "--resolve-finding", "unresolved finding",
                    "--evidence-ref", "evidence/resolution.json")

    assert resolving.returncode == 0, resolving.stderr
    active = json.loads(state_path.read_text(encoding="utf-8"))["active_work"]
    assert active["pending_findings"] == []
    assert active["evidence_refs"] == ["evidence/resolution.json"]
    rows = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines()]
    assert rows[1]["active_work_patch"]["resolve_findings"] == ["unresolved finding"]


def test_unknown_finding_resolution_leaves_state_and_ledger_unchanged(tmp_path):
    state_path = tmp_path / "state.json"
    ledger_path = tmp_path / "execution_ledger.jsonl"
    state_fixture(state_path)
    before = state_path.read_bytes()

    result = cli(state_path, ledger_path, "--expected-revision", "4", "--phase", "AUDIT",
                 "--next-action", "close finding", "--resolve-finding", "not tracked")

    assert result.returncode != 0
    assert "not tracked" in result.stderr
    assert state_path.read_bytes() == before
    assert not ledger_path.exists()


def test_implementation_phase_fails_closed_for_missing_or_unknown_work_mode(tmp_path):
    for mode in (None, "UNRECOGNIZED"):
        case = tmp_path / str(mode)
        case.mkdir()
        state_path = case / "state.json"
        ledger_path = case / "execution_ledger.jsonl"
        state = state_fixture(state_path)
        if mode is None:
            del state["work_mode"]
        else:
            state["work_mode"] = mode
        state_path.write_text(json.dumps(state), encoding="utf-8")
        before = state_path.read_bytes()

        result = cli(state_path, ledger_path, "--expected-revision", "4", "--phase", "IMPLEMENT",
                     "--next-action", "implement")

        assert result.returncode != 0
        assert "work_mode" in result.stderr
        assert state_path.read_bytes() == before
        assert not ledger_path.exists()


def test_implementation_phase_requires_execution_authorization_when_present(tmp_path):
    state_path = tmp_path / "state.json"
    ledger_path = tmp_path / "execution_ledger.jsonl"
    state = state_fixture(state_path)
    state["execution_authorized"] = False
    state_path.write_text(json.dumps(state), encoding="utf-8")
    before = state_path.read_bytes()

    result = cli(state_path, ledger_path, "--expected-revision", "4", "--phase", "TDD_RED",
                 "--next-action", "record red tests")

    assert result.returncode != 0
    assert "execution_authorized" in result.stderr
    assert state_path.read_bytes() == before


def test_implementation_phase_cannot_select_task_after_current_earliest_gate(tmp_path):
    state_path = tmp_path / "state.json"
    ledger_path = tmp_path / "execution_ledger.jsonl"
    state = state_fixture(state_path)
    state["current_slice"] = "S00"
    state["slices"] = {
        "S00": {"status": "IN_PROGRESS", "gates": {"GATE-1": "NOT_RUN"}},
        "S01": {"status": "NOT_STARTED", "gates": {"GATE-1": "NOT_RUN"}},
    }
    state["active_work"]["work_package_id"] = "S01-T01"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    before = state_path.read_bytes()

    result = cli(state_path, ledger_path, "--expected-revision", "4", "--phase", "IMPLEMENT",
                 "--next-action", "implement downstream task")

    assert result.returncode != 0
    assert "slice" in result.stderr.lower()
    assert state_path.read_bytes() == before


def test_io_failure_emits_structured_checkpoint_pending_recovery_action(tmp_path, monkeypatch, capsys):
    import importlib.util

    spec = importlib.util.spec_from_file_location("checkpoint_execution_io_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    state_path = tmp_path / "state.json"
    ledger_path = tmp_path / "execution_ledger.jsonl"
    state_fixture(state_path)

    def fail_io(*_args, **_kwargs):
        raise OSError(5, "simulated fsync failure")

    monkeypatch.setattr(module, "update", fail_io)
    code = module.main(["--state", str(state_path), "--ledger", str(ledger_path), "--expected-revision", "4",
                        "--phase", "AUDIT", "--next-action", "recover checkpoint"])

    captured = capsys.readouterr()
    assert code != 0
    diagnostic = json.loads(captured.err)
    assert diagnostic["status"] == "CHECKPOINT_PENDING"
    assert diagnostic["failure_class"] == "IO_OR_FSYNC_ERROR"
    assert "--expected-revision 4" in diagnostic["recovery_next_action"]


def test_cli_rejects_corrupt_state_shape_before_writing(tmp_path):
    state_path = tmp_path / "state.json"
    ledger_path = tmp_path / "execution_ledger.jsonl"
    state_path.write_text("[]\n", encoding="utf-8")
    before = state_path.read_bytes()

    result = cli(state_path, ledger_path, "--expected-revision", "4", "--phase", "AUDIT",
                 "--next-action", "resume")

    assert result.returncode != 0
    assert "state" in result.stderr.lower()
    assert "Traceback" not in result.stderr
    assert state_path.read_bytes() == before
    assert not ledger_path.exists()


def test_cli_rejects_invalid_revision_and_missing_active_work_before_writing(tmp_path):
    for label, state in (
        ("boolean-revision", {"revision": True, "active_work": {}}),
        ("missing-active-work", {"revision": 4}),
    ):
        case = tmp_path / label
        case.mkdir()
        state_path = case / "state.json"
        ledger_path = case / "execution_ledger.jsonl"
        state_path.write_text(json.dumps(state), encoding="utf-8")
        before = state_path.read_bytes()

        result = cli(state_path, ledger_path, "--expected-revision", "4", "--phase", "AUDIT",
                     "--next-action", "resume")

        assert result.returncode != 0
        assert "state" in result.stderr.lower()
        assert "Traceback" not in result.stderr
        assert state_path.read_bytes() == before
        assert not ledger_path.exists()


def test_cli_fails_closed_when_slice_authority_is_missing_or_inconsistent(tmp_path):
    invalid_states = (
        ("missing-slices", lambda state: state.pop("slices")),
        ("empty-slices", lambda state: state.update(slices={})),
        ("missing-current-slice", lambda state: state.pop("current_slice")),
        ("unknown-current-slice", lambda state: state.update(current_slice="S99")),
    )
    for label, invalidate in invalid_states:
        case = tmp_path / label
        case.mkdir()
        state_path = case / "state.json"
        ledger_path = case / "execution_ledger.jsonl"
        state = state_fixture(state_path)
        invalidate(state)
        state_path.write_text(json.dumps(state), encoding="utf-8")
        before = state_path.read_bytes()

        result = cli(state_path, ledger_path, "--expected-revision", "4", "--phase", "IMPLEMENT",
                     "--next-action", "continue")

        assert result.returncode != 0
        assert "slice" in result.stderr.lower()
        assert state_path.read_bytes() == before
        assert not ledger_path.exists()


def test_slice_order_uses_canonical_names_not_json_insertion_order(tmp_path):
    state_path = tmp_path / "state.json"
    ledger_path = tmp_path / "execution_ledger.jsonl"
    state = state_fixture(state_path)
    state["current_slice"] = "S01"
    state["active_work"]["work_package_id"] = "S01-T01"
    state["slices"] = {
        "S01": {"status": "IN_PROGRESS", "gates": {"S01-GATE-01": "NOT_RUN"}},
        "S00": {"status": "IN_PROGRESS", "gates": {"S00-GATE-01": "NOT_RUN"}},
    }
    state_path.write_text(json.dumps(state), encoding="utf-8")
    before = state_path.read_bytes()

    result = cli(state_path, ledger_path, "--expected-revision", "4", "--phase", "IMPLEMENT",
                 "--next-action", "must not skip earlier slice")

    assert result.returncode != 0
    assert "slice" in result.stderr.lower()
    assert state_path.read_bytes() == before
    assert not ledger_path.exists()
