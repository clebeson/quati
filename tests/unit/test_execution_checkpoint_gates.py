"""Public CLI coverage for journaled slice-gate updates in checkpoint_execution.py.

A gate may become PASS only with indexed, hash-verified TESTS_VERIFIED and
EVIDENCE_VERIFIED seal records whose scope covers that gate or its slice. Every
rejected update must leave the canonical state bytes and the ledger untouched.
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "checkpoint_execution.py"
COMMIT = "a" * 40
BLOCKER = "S00-GATE-02 requires verified provider configuration"


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def write_state(root):
    def slice_item(prefix, status):
        gates = {f"{prefix}-GATE-01": "NOT_RUN", f"{prefix}-GATE-02": "BLOCKED"}
        return {
            "status": status,
            "gates": gates,
            "evidence_refs": ["evidence/old.txt"],
            "blockers": [BLOCKER] if prefix == "S00" else [],
            "commit": None,
            "gate_seal_refs": {gate: [] for gate in gates},
        }

    state = {
        "revision": 7,
        "work_mode": "IMPLEMENTATION_AUTHORIZED",
        "execution_authorized": True,
        "current_slice": "S00",
        "slices": {"S00": slice_item("S00", "IN_PROGRESS"), "S01": slice_item("S01", "NOT_STARTED")},
        "active_work": {
            "work_package_id": "S00-T05",
            "phase": "AUDIT",
            "completed_steps": ["live run recorded"],
            "next_action": "seal the gate",
        },
        "other": {"preserve": True},
    }
    path = root / "state.json"
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return path


def write_seal(root, seal_id, kind, scope_ids, verdict="PASS"):
    relative = f"governance/seals/{seal_id}.json"
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    record = {"seal_id": seal_id, "kind": kind, "scope_ids": scope_ids, "verdict": verdict}
    target.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return {
        "seal_id": seal_id,
        "path": relative,
        "record_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "kind": kind,
        "scope_ids": scope_ids,
        "supersedes": None,
    }


def write_index(root, records):
    path = root / "governance" / "seals" / "index.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": "secma-seal-index/1", "records": records}, indent=2) + "\n",
                    encoding="utf-8")
    return path


def workspace(tmp_path, records=None):
    state_path = write_state(tmp_path)
    if records is None:
        records = [
            write_seal(tmp_path, "S00-GATE-02-TESTS-001", "TESTS_VERIFIED", ["S00-GATE-02"]),
            write_seal(tmp_path, "S00-GATE-02-EVIDENCE-001", "EVIDENCE_VERIFIED", ["S00"]),
        ]
    write_index(tmp_path, records)
    return state_path, tmp_path / "execution_ledger.jsonl", records


def cli(tmp_path, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--state", str(tmp_path / "state.json"),
         "--ledger", str(tmp_path / "execution_ledger.jsonl"),
         "--seal-index", str(tmp_path / "governance" / "seals" / "index.json"),
         "--seal-root", str(tmp_path),
         "--expected-revision", "7", "--phase", "CHECKPOINT", "--next-action", "run the next gate",
         *map(str, args)],
        cwd=ROOT, capture_output=True, text=True,
    )


PASS_ARGS = (
    "--gate", "S00-GATE-02=PASS",
    "--gate-seal", "S00-GATE-02=S00-GATE-02-TESTS-001",
    "--gate-seal", "S00-GATE-02=S00-GATE-02-EVIDENCE-001",
    "--slice-commit", COMMIT,
)


def assert_rejected(tmp_path, result, state_path, before, fragment):
    assert result.returncode == 2, result.stdout + result.stderr
    assert fragment in result.stderr
    assert state_path.read_bytes() == before
    assert not (tmp_path / "execution_ledger.jsonl").exists()
    assert not (tmp_path / "execution_journal").exists()


def test_gate_pass_records_exact_seal_refs_commit_and_journal_event(tmp_path):
    state_path, ledger_path, records = workspace(tmp_path)
    original = json.loads(state_path.read_text(encoding="utf-8"))

    result = cli(tmp_path, *PASS_ARGS, "--slice-evidence-ref", "evidence/gate6/INDEX.json",
                 "--resolve-blocker", BLOCKER, "--slice-blocker", "LOG-0034 live negative lines remain debt",
                 "--step", "gate sealed")

    assert result.returncode == 0, result.stderr
    updated = json.loads(state_path.read_text(encoding="utf-8"))
    item = updated["slices"]["S00"]
    assert updated["revision"] == 8
    assert item["gates"] == {"S00-GATE-01": "NOT_RUN", "S00-GATE-02": "PASS"}
    assert item["status"] == "IN_PROGRESS"
    assert item["commit"] == COMMIT
    assert item["evidence_refs"] == ["evidence/old.txt", "evidence/gate6/INDEX.json"]
    assert item["blockers"] == ["LOG-0034 live negative lines remain debt"]
    assert item["gate_seal_refs"]["S00-GATE-01"] == []
    assert item["gate_seal_refs"]["S00-GATE-02"] == [
        {"seal_id": record["seal_id"], "path": record["path"], "record_sha256": record["record_sha256"],
         "kind": record["kind"], "scope_id": scope}
        for record, scope in zip(records, ["S00-GATE-02", "S00"])
    ]
    assert updated["slices"]["S01"] == original["slices"]["S01"]
    assert updated["other"] == {"preserve": True}
    assert updated["active_work"]["completed_steps"] == ["live run recorded", "gate sealed"]

    rows = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    row = rows[0]
    assert row["revision"] == 8
    assert row["state_before_sha256"] == digest(original)
    assert row["state_sha256"] == digest(updated)
    assert row["slice_patch"]["slice_id"] == "S00"
    assert row["slice_patch"]["gates"] == {"S00-GATE-02": "PASS"}
    assert row["slice_patch"]["commit"] == COMMIT
    assert [ref["seal_id"] for ref in row["slice_patch"]["gate_seal_refs"]["S00-GATE-02"]] == [
        "S00-GATE-02-TESTS-001", "S00-GATE-02-EVIDENCE-001"]
    event = {key: value for key, value in row.items() if key != "event_hash"}
    assert row["event_hash"] == digest(event)


def test_checkpoint_without_slice_options_keeps_the_event_shape(tmp_path):
    state_path, ledger_path, _ = workspace(tmp_path)
    before = json.loads(state_path.read_text(encoding="utf-8"))

    result = cli(tmp_path, "--step", "progress only")

    assert result.returncode == 0, result.stderr
    row = json.loads(ledger_path.read_text(encoding="utf-8").splitlines()[0])
    assert "slice_patch" not in row
    assert json.loads(state_path.read_text(encoding="utf-8"))["slices"] == before["slices"]


def test_gate_pass_without_seals_is_rejected(tmp_path):
    state_path, _, _ = workspace(tmp_path)
    before = state_path.read_bytes()
    result = cli(tmp_path, "--gate", "S00-GATE-02=PASS", "--slice-commit", COMMIT)
    assert_rejected(tmp_path, result, state_path, before, "TESTS_VERIFIED and EVIDENCE_VERIFIED")


def test_gate_pass_with_only_tests_verified_is_rejected(tmp_path):
    state_path, _, _ = workspace(tmp_path)
    before = state_path.read_bytes()
    result = cli(tmp_path, "--gate", "S00-GATE-02=PASS", "--slice-commit", COMMIT,
                 "--gate-seal", "S00-GATE-02=S00-GATE-02-TESTS-001")
    assert_rejected(tmp_path, result, state_path, before, "TESTS_VERIFIED and EVIDENCE_VERIFIED")


def test_gate_pass_without_a_slice_commit_is_rejected(tmp_path):
    state_path, _, _ = workspace(tmp_path)
    before = state_path.read_bytes()
    result = cli(tmp_path, *PASS_ARGS[:-2])
    assert_rejected(tmp_path, result, state_path, before, "requires a slice commit")


def test_seal_missing_from_index_is_rejected(tmp_path):
    state_path, _, _ = workspace(tmp_path)
    before = state_path.read_bytes()
    result = cli(tmp_path, "--gate", "S00-GATE-02=BLOCKED", "--gate-seal", "S00-GATE-02=UNKNOWN-SEAL")
    assert_rejected(tmp_path, result, state_path, before, "Seal not in canonical index")


def test_changed_seal_record_is_rejected(tmp_path):
    state_path, _, records = workspace(tmp_path)
    record_path = tmp_path / records[0]["path"]
    record_path.write_text(record_path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    before = state_path.read_bytes()
    result = cli(tmp_path, *PASS_ARGS)
    assert_rejected(tmp_path, result, state_path, before, "Seal record changed")


def test_seal_scope_must_cover_the_gate_or_its_slice(tmp_path):
    records = [
        write_seal(tmp_path, "S00-GATE-02-TESTS-001", "TESTS_VERIFIED", ["S00-GATE-01"]),
        write_seal(tmp_path, "S00-GATE-02-EVIDENCE-001", "EVIDENCE_VERIFIED", ["S00"]),
    ]
    state_path, _, _ = workspace(tmp_path, records)
    before = state_path.read_bytes()
    result = cli(tmp_path, *PASS_ARGS)
    assert_rejected(tmp_path, result, state_path, before, "Seal scope does not cover")


def test_nonpassing_seal_cannot_support_a_pass_gate(tmp_path):
    records = [
        write_seal(tmp_path, "S00-GATE-02-TESTS-001", "TESTS_VERIFIED", ["S00-GATE-02"], verdict="FAIL"),
        write_seal(tmp_path, "S00-GATE-02-EVIDENCE-001", "EVIDENCE_VERIFIED", ["S00"]),
    ]
    state_path, _, _ = workspace(tmp_path, records)
    before = state_path.read_bytes()
    result = cli(tmp_path, *PASS_ARGS)
    assert_rejected(tmp_path, result, state_path, before, "Nonpassing seal")


def test_seal_record_identity_must_match_the_index(tmp_path):
    records = [
        write_seal(tmp_path, "S00-GATE-02-TESTS-001", "TESTS_VERIFIED", ["S00-GATE-02"]),
        write_seal(tmp_path, "S00-GATE-02-EVIDENCE-001", "EVIDENCE_VERIFIED", ["S00"]),
    ]
    records[1]["kind"] = "TESTS_VERIFIED"
    state_path, _, _ = workspace(tmp_path, records)
    before = state_path.read_bytes()
    result = cli(tmp_path, *PASS_ARGS)
    assert_rejected(tmp_path, result, state_path, before, "Seal index and record disagree")


def test_seal_path_cannot_escape_the_seal_root(tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside.json"
    outside.write_text("{}", encoding="utf-8")
    records = [
        {"seal_id": "S00-GATE-02-TESTS-001", "path": f"../{outside.name}",
         "record_sha256": hashlib.sha256(b"{}").hexdigest(), "kind": "TESTS_VERIFIED",
         "scope_ids": ["S00-GATE-02"], "supersedes": None},
    ]
    state_path, _, _ = workspace(tmp_path, records)
    before = state_path.read_bytes()
    result = cli(tmp_path, "--gate", "S00-GATE-02=BLOCKED", "--gate-seal", "S00-GATE-02=S00-GATE-02-TESTS-001")
    assert_rejected(tmp_path, result, state_path, before, "Seal path escapes")


def test_duplicate_seal_identity_in_index_is_rejected(tmp_path):
    record = write_seal(tmp_path, "S00-GATE-02-TESTS-001", "TESTS_VERIFIED", ["S00-GATE-02"])
    state_path, _, _ = workspace(tmp_path, [record, dict(record)])
    before = state_path.read_bytes()
    result = cli(tmp_path, "--gate", "S00-GATE-02=BLOCKED", "--gate-seal", "S00-GATE-02=S00-GATE-02-TESTS-001")
    assert_rejected(tmp_path, result, state_path, before, "Duplicate seal identity")


def test_unknown_gate_and_gates_of_two_slices_are_rejected(tmp_path):
    state_path, _, _ = workspace(tmp_path)
    before = state_path.read_bytes()
    result = cli(tmp_path, "--gate", "S09-GATE-01=BLOCKED")
    assert_rejected(tmp_path, result, state_path, before, "Unknown gate")
    result = cli(tmp_path, "--gate", "S00-GATE-01=BLOCKED", "--gate", "S01-GATE-01=BLOCKED")
    assert_rejected(tmp_path, result, state_path, before, "one slice")


def test_gate_of_a_later_slice_is_rejected(tmp_path):
    state_path, _, _ = workspace(tmp_path)
    before = state_path.read_bytes()
    result = cli(tmp_path, "--gate", "S01-GATE-01=FAIL")
    assert_rejected(tmp_path, result, state_path, before, "beyond current/earliest incomplete slice")


def test_malformed_gate_arguments_are_rejected(tmp_path):
    state_path, _, _ = workspace(tmp_path)
    before = state_path.read_bytes()
    for arguments, fragment in (
        (("--gate", "S00-GATE-02"), "GATE=STATUS"),
        (("--gate", "S00-GATE-02=DONE"), "Unsupported gate status"),
        (("--gate", "S00-GATE-02=FAIL", "--gate", "S00-GATE-02=BLOCKED"), "Duplicate gate"),
        (("--gate", "S00-GATE-02=BLOCKED", "--gate-seal", "S00-GATE-02"), "GATE=SEAL_ID"),
        (("--gate", "S00-GATE-02=BLOCKED", "--slice-commit", "not-a-sha"), "commit must be"),
        (("--gate", "S00-GATE-02=BLOCKED", "--slice-evidence-ref", " "), "non-empty"),
    ):
        result = cli(tmp_path, *arguments)
        assert_rejected(tmp_path, result, state_path, before, fragment)


def test_slice_options_without_a_gate_or_slice_are_rejected(tmp_path):
    state_path, _, _ = workspace(tmp_path)
    before = state_path.read_bytes()
    result = cli(tmp_path, "--slice-commit", COMMIT)
    assert_rejected(tmp_path, result, state_path, before, "require --gate or --slice")


def test_slice_option_must_agree_with_the_gates(tmp_path):
    state_path, _, _ = workspace(tmp_path)
    before = state_path.read_bytes()
    result = cli(tmp_path, "--slice", "S01", "--gate", "S00-GATE-02=BLOCKED")
    assert_rejected(tmp_path, result, state_path, before, "one slice")
    result = cli(tmp_path, "--slice", "S09", "--slice-evidence-ref", "evidence/x.txt")
    assert_rejected(tmp_path, result, state_path, before, "Unknown slice")


def test_unknown_blocker_resolution_is_rejected(tmp_path):
    state_path, _, _ = workspace(tmp_path)
    before = state_path.read_bytes()
    result = cli(tmp_path, "--slice", "S00", "--resolve-blocker", "never recorded")
    assert_rejected(tmp_path, result, state_path, before, "Cannot resolve untracked blocker")


def test_nonpassing_status_needs_no_seal_and_keeps_existing_refs(tmp_path):
    state_path, ledger_path, _ = workspace(tmp_path)
    assert cli(tmp_path, *PASS_ARGS).returncode == 0
    sealed = json.loads(state_path.read_text(encoding="utf-8"))["slices"]["S00"]["gate_seal_refs"]["S00-GATE-02"]

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--state", str(state_path), "--ledger", str(ledger_path),
         "--seal-index", str(tmp_path / "governance" / "seals" / "index.json"), "--seal-root", str(tmp_path),
         "--expected-revision", "8", "--phase", "AUDIT", "--next-action", "reconcile the invalid seal",
         "--gate", "S00-GATE-02=BLOCKED", "--gate", "S00-GATE-01=FAIL",
         "--slice-blocker", "seal invalidated by a code change"],
        cwd=ROOT, capture_output=True, text=True,
    )

    assert result.returncode == 0, result.stderr
    item = json.loads(state_path.read_text(encoding="utf-8"))["slices"]["S00"]
    assert item["gates"] == {"S00-GATE-01": "FAIL", "S00-GATE-02": "BLOCKED"}
    assert item["gate_seal_refs"]["S00-GATE-02"] == sealed
    assert item["commit"] == COMMIT
    assert item["blockers"] == [BLOCKER, "seal invalidated by a code change"]
    rows = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines()]
    assert [row["revision"] for row in rows] == [8, 9]
    assert rows[1]["previous_hash"] == rows[0]["event_hash"]


def test_pass_gate_already_sealed_does_not_duplicate_refs(tmp_path):
    state_path, ledger_path, _ = workspace(tmp_path)
    assert cli(tmp_path, *PASS_ARGS).returncode == 0

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--state", str(state_path), "--ledger", str(ledger_path),
         "--seal-index", str(tmp_path / "governance" / "seals" / "index.json"), "--seal-root", str(tmp_path),
         "--expected-revision", "8", "--phase", "CHECKPOINT", "--next-action", "continue",
         "--gate", "S00-GATE-02=PASS", "--gate-seal", "S00-GATE-02=S00-GATE-02-TESTS-001"],
        cwd=ROOT, capture_output=True, text=True,
    )

    assert result.returncode == 0, result.stderr
    refs = json.loads(state_path.read_text(encoding="utf-8"))["slices"]["S00"]["gate_seal_refs"]["S00-GATE-02"]
    assert [ref["seal_id"] for ref in refs] == ["S00-GATE-02-TESTS-001", "S00-GATE-02-EVIDENCE-001"]


def test_missing_seal_index_is_rejected_only_when_a_seal_is_named(tmp_path):
    state_path, _, _ = workspace(tmp_path)
    (tmp_path / "governance" / "seals" / "index.json").unlink()
    before = state_path.read_bytes()
    result = cli(tmp_path, "--gate", "S00-GATE-02=BLOCKED", "--gate-seal", "S00-GATE-02=S00-GATE-02-TESTS-001")
    assert_rejected(tmp_path, result, state_path, before, "Seal index")
    assert cli(tmp_path, "--gate", "S00-GATE-01=IN_PROGRESS").returncode == 0


def test_missing_and_malformed_seal_records_are_rejected(tmp_path):
    state_path, _, records = workspace(tmp_path)
    before = state_path.read_bytes()
    record_path = tmp_path / records[0]["path"]
    record_path.unlink()
    result = cli(tmp_path, *PASS_ARGS)
    assert_rejected(tmp_path, result, state_path, before, "Missing seal record")

    record_path.write_text('["not", "a", "seal"]', encoding="utf-8")
    records[0]["record_sha256"] = hashlib.sha256(record_path.read_bytes()).hexdigest()
    write_index(tmp_path, records)
    result = cli(tmp_path, *PASS_ARGS)
    assert_rejected(tmp_path, result, state_path, before, "not a valid seal")


def test_existing_reference_that_disagrees_with_the_index_is_rejected(tmp_path):
    state_path, _, records = workspace(tmp_path)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["slices"]["S00"]["gate_seal_refs"]["S00-GATE-02"] = [{
        "seal_id": records[0]["seal_id"], "path": records[0]["path"], "record_sha256": "0" * 64,
        "kind": "TESTS_VERIFIED", "scope_id": "S00-GATE-02"}]
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    before = state_path.read_bytes()
    result = cli(tmp_path, *PASS_ARGS)
    assert_rejected(tmp_path, result, state_path, before, "Seal reference conflict")


def _second_cli(tmp_path, revision, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--state", str(tmp_path / "state.json"),
         "--ledger", str(tmp_path / "execution_ledger.jsonl"),
         "--seal-index", str(tmp_path / "governance" / "seals" / "index.json"), "--seal-root", str(tmp_path),
         "--expected-revision", str(revision), "--phase", "CHECKPOINT", "--next-action", "continue",
         *map(str, args)],
        cwd=ROOT, capture_output=True, text=True,
    )


def test_a_superseding_seal_replaces_the_reference_it_names(tmp_path):
    state_path, ledger_path, records = workspace(tmp_path)
    assert cli(tmp_path, *PASS_ARGS).returncode == 0
    newer_tests = write_seal(tmp_path, "S00-GATE-02-TESTS-002", "TESTS_VERIFIED", ["S00-GATE-02"])
    newer_tests["supersedes"] = "S00-GATE-02-TESTS-001"
    newer_evidence = write_seal(tmp_path, "S00-GATE-02-EVIDENCE-002", "EVIDENCE_VERIFIED", ["S00"])
    newer_evidence["supersedes"] = "S00-GATE-02-EVIDENCE-001"
    write_index(tmp_path, [*records, newer_tests, newer_evidence])

    result = _second_cli(tmp_path, 8, "--gate", "S00-GATE-02=PASS", "--slice-commit", "b" * 40,
                         "--gate-seal", "S00-GATE-02=S00-GATE-02-TESTS-002",
                         "--gate-seal", "S00-GATE-02=S00-GATE-02-EVIDENCE-002")

    assert result.returncode == 0, result.stderr
    item = json.loads(state_path.read_text(encoding="utf-8"))["slices"]["S00"]
    assert [ref["seal_id"] for ref in item["gate_seal_refs"]["S00-GATE-02"]] == [
        "S00-GATE-02-TESTS-002", "S00-GATE-02-EVIDENCE-002"]
    assert item["commit"] == "b" * 40
    row = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines()][-1]
    assert row["slice_patch"]["superseded_seal_refs"] == {
        "S00-GATE-02": ["S00-GATE-02-TESTS-001", "S00-GATE-02-EVIDENCE-001"]}


def test_superseding_only_one_kind_leaves_a_pass_gate_without_its_pair_rejected(tmp_path):
    state_path, _, records = workspace(tmp_path)
    assert cli(tmp_path, *PASS_ARGS).returncode == 0
    odd = write_seal(tmp_path, "S00-GATE-02-AUDIT-002", "INDEPENDENT_AUDIT_PASSED", ["S00-GATE-02"])
    odd["supersedes"] = "S00-GATE-02-TESTS-001"
    write_index(tmp_path, [*records, odd])
    before = state_path.read_bytes()

    result = _second_cli(tmp_path, 8, "--gate", "S00-GATE-02=PASS",
                         "--gate-seal", "S00-GATE-02=S00-GATE-02-AUDIT-002")

    assert result.returncode == 2
    assert "TESTS_VERIFIED and EVIDENCE_VERIFIED" in result.stderr
    assert state_path.read_bytes() == before


def test_a_seal_that_supersedes_nothing_referenced_keeps_existing_references(tmp_path):
    state_path, _, records = workspace(tmp_path)
    assert cli(tmp_path, *PASS_ARGS).returncode == 0
    extra = write_seal(tmp_path, "S00-GATE-02-AUDIT-001", "INDEPENDENT_AUDIT_PASSED", ["S00-GATE-02"])
    extra["supersedes"] = "SOME-OTHER-SEAL"
    write_index(tmp_path, [*records, extra])

    result = _second_cli(tmp_path, 8, "--gate", "S00-GATE-02=PASS",
                         "--gate-seal", "S00-GATE-02=S00-GATE-02-AUDIT-001")

    assert result.returncode == 0, result.stderr
    refs = json.loads(state_path.read_text(encoding="utf-8"))["slices"]["S00"]["gate_seal_refs"]["S00-GATE-02"]
    assert [ref["seal_id"] for ref in refs] == [
        "S00-GATE-02-TESTS-001", "S00-GATE-02-EVIDENCE-001", "S00-GATE-02-AUDIT-001"]
