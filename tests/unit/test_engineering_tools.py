"""Requirement: resumable engineering helpers must preserve truthful, secret-safe evidence."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PYTHON = Path(sys.executable).absolute()


def cli(script, *args, **kwargs):
    return subprocess.run(
        [str(PYTHON), str(ROOT / "scripts" / script), *map(str, args)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        **kwargs,
    )


def test_checkpoint_state_requires_cas_and_never_skips_incomplete_slice(tmp_path):
    state = json.loads((ROOT / "docs/implementation/implementation_state.json").read_text())
    state["revision"] = 0
    path = tmp_path / "state.json"
    path.write_text(json.dumps(state))

    result = cli("checkpoint_state.py", "--state", path, "--expected-revision", "1", "--slice", "S00", "--status", "IN_PROGRESS")
    assert result.returncode != 0
    result = cli("checkpoint_state.py", "--state", path, "--expected-revision", "0", "--slice", "S00", "--status", "PASS")
    assert result.returncode != 0
    result = cli("checkpoint_state.py", "--state", path, "--expected-revision", "0", "--advance-to", "S01")
    assert result.returncode != 0
    assert json.loads(path.read_text())["revision"] == 0


def test_checkpoint_state_writes_atomically_with_revision_and_gates(tmp_path):
    state = json.loads((ROOT / "docs/implementation/implementation_state.json").read_text())
    state["revision"] = 0
    path = tmp_path / "state.json"
    path.write_text(json.dumps(state))
    result = cli("checkpoint_state.py", "--state", path, "--expected-revision", "0", "--slice", "S00", "--status", "IN_PROGRESS", "--gate", "S00-GATE-01=PASS")
    assert result.returncode == 0, result.stderr
    after = json.loads(path.read_text())
    assert after["revision"] == 1
    assert after["slices"]["S00"]["status"] == "IN_PROGRESS"
    assert after["slices"]["S00"]["gates"]["S00-GATE-01"] == "PASS"


@pytest.mark.parametrize("artifact", ["execution_ledger.jsonl", "execution_journal"])
def test_checkpoint_state_refuses_journaled_state(tmp_path, artifact):
    """Fail closed: legacy writes beside a ledger/journal would brick checkpoint_execution.py."""
    path = tmp_path / "implementation_state.json"
    original = json.dumps({"revision": 0, "current_slice": "S00",
                           "slices": {"S00": {"status": "NOT_STARTED", "gates": {"S00-GATE-01": "NOT_RUN"}}}})
    path.write_text(original)
    if artifact.endswith(".jsonl"):
        (tmp_path / artifact).write_text("")
    else:
        (tmp_path / artifact).mkdir()
    result = cli("checkpoint_state.py", "--state", path, "--expected-revision", "0", "--slice", "S00", "--status", "IN_PROGRESS")
    assert result.returncode == 2
    assert "checkpoint_execution.py" in result.stderr
    assert path.read_text() == original
    assert not path.with_name(path.name + ".lock").exists()


def test_checkpoint_state_updates_unjournaled_state(tmp_path):
    path = tmp_path / "implementation_state.json"
    path.write_text(json.dumps({"revision": 0, "current_slice": "S00",
                                "slices": {"S00": {"status": "NOT_STARTED", "gates": {"S00-GATE-01": "NOT_RUN"}}}}))
    result = cli("checkpoint_state.py", "--state", path, "--expected-revision", "0", "--slice", "S00", "--status", "IN_PROGRESS")
    assert result.returncode == 0, result.stderr
    after = json.loads(path.read_text())
    assert after["revision"] == 1 and after["slices"]["S00"]["status"] == "IN_PROGRESS"


def test_record_evidence_redacts_secret_and_omits_arguments(tmp_path):
    secret = "fixture-secret-do-not-persist"
    evdir = tmp_path / "evidence"
    result = cli(
        "record_evidence.py", "--evidence-dir", evdir, "--source", ROOT / "AGENTS.md", "--",
        str(PYTHON), "-c", f"import sys; print(sys.argv[1]); print('{secret}', file=sys.stderr)", secret,
        env={**os.environ, "QUATI_API_KEY_ENV": "QUATI_TEST_SECRET", "QUATI_TEST_SECRET": secret},
    )
    assert result.returncode == 0, result.stderr
    runs = list(evdir.iterdir())
    assert len(runs) == 1
    manifest = json.loads((runs[0] / "manifest.json").read_text())
    out = (runs[0] / "stdout.txt").read_text()
    err = (runs[0] / "stderr.txt").read_text()
    assert secret not in out + err + json.dumps(manifest)
    assert manifest["command"]["arguments_omitted"] is True
    assert "scripts/record_evidence.py" in manifest["source_sha256"]
    assert manifest["stdout_sha256"] == hashlib.sha256(out.encode()).hexdigest()
    assert (runs[0].stat().st_mode & 0o777) == 0o700
    assert all((p.stat().st_mode & 0o777) == 0o600 for p in runs[0].iterdir())


def test_record_evidence_preserves_failure_exit_and_never_overwrites(tmp_path):
    evdir = tmp_path / "evidence"
    for _ in range(2):
        result = cli("record_evidence.py", "--evidence-dir", evdir, "--", str(PYTHON), "-c", "raise SystemExit(7)")
        assert result.returncode == 7
    assert len(list(evdir.iterdir())) == 2
    assert all(json.loads((p / "manifest.json").read_text())["exit_code"] == 7 for p in evdir.iterdir())
