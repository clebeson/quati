"""Adversarial public-helper tests for LOG-0054 H1-H6; engineering proof only."""

import hashlib
import json
import subprocess
import sys

import pytest

from test_execution_checkpoint_gates import (
    BLOCKER, COMMIT, PASS_ARGS, ROOT, SCRIPT, _acceptance_args, _second_cli, _slice_workspace,
    cli, workspace, write_index, write_seal,
)


def _checkpoint_bytes(root):
    paths = [root / 'state.json', root / 'execution_ledger.jsonl']
    paths.extend(sorted((root / 'execution_journal').glob('*.json')))
    return {str(path): path.read_bytes() for path in paths if path.exists()}


def _rejected(root, revision, *arguments):
    before = _checkpoint_bytes(root)
    result = _second_cli(root, revision, *arguments)
    assert result.returncode == 2, (result.stdout, result.stderr)
    assert _checkpoint_bytes(root) == before
    return result.stderr


def _edit_seal(root, seal_id, **changes):
    index_path = root / 'governance/seals/index.json'
    index = json.loads(index_path.read_text())
    entry = next(row for row in index['records'] if row['seal_id'] == seal_id)
    path = root / entry['path']
    record = json.loads(path.read_text())
    record.update(changes)
    record = {key: value for key, value in record.items() if value is not None}
    path.write_text(json.dumps(record))
    entry['record_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    write_index(root, index['records'])


@pytest.mark.parametrize('verdict', ['FAIL', 'BLOCKED'])
def test_nonpassing_acceptance_cannot_promote_a_slice(tmp_path, verdict):
    _slice_workspace(tmp_path)
    _edit_seal(tmp_path, 'S00-ACCEPTED-001', verdict=verdict)
    _rejected(tmp_path, 8, *_acceptance_args(), '--advance-to', 'S01')


@pytest.mark.parametrize('operation', ['accept', 'advance'])
@pytest.mark.parametrize('damage', ['bytes', 'missing', 'deindexed', 'verdict', 'source', 'superseded'])
def test_retained_seals_are_verified_on_acceptance_and_advance(tmp_path, operation, damage):
    _slice_workspace(tmp_path)
    revision = 8
    if operation == 'advance':
        result = _second_cli(tmp_path, 8, *_acceptance_args())
        assert result.returncode == 0, result.stderr
        revision = 9
    seal_id = 'S00-TESTS-001'
    path = tmp_path / f'governance/seals/{seal_id}.json'
    if damage == 'bytes':
        path.write_bytes(path.read_bytes() + b' ')
    elif damage == 'missing':
        path.unlink()
    elif damage == 'deindexed':
        index = json.loads((tmp_path / 'governance/seals/index.json').read_text())
        write_index(tmp_path, [row for row in index['records'] if row['seal_id'] != seal_id])
    elif damage == 'verdict':
        _edit_seal(tmp_path, seal_id, verdict='FAIL')
    elif damage == 'source':
        _edit_seal(tmp_path, seal_id, commit_evidence={'commit_sha': 'b' * 40})
    else:
        index = json.loads((tmp_path / 'governance/seals/index.json').read_text())
        replacement = write_seal(tmp_path, 'S00-TESTS-002', 'TESTS_VERIFIED', ['S00'])
        replacement['supersedes'] = seal_id
        write_index(tmp_path, [*index['records'], replacement])
    arguments = _acceptance_args() if operation == 'accept' else ['--advance-to', 'S01']
    _rejected(tmp_path, revision, *arguments)


def test_gate_seals_must_match_the_recorded_source_commit(tmp_path):
    workspace(tmp_path)
    _rejected(tmp_path, 7, *PASS_ARGS[:-1], 'b' * 40)


def test_commit_only_patch_cannot_rebind_an_accepted_slice(tmp_path):
    _slice_workspace(tmp_path)
    assert _second_cli(tmp_path, 8, *_acceptance_args()).returncode == 0
    _rejected(tmp_path, 9, '--slice', 'S00', '--slice-commit', 'b' * 40)


def test_acceptance_rejects_unresolved_blockers(tmp_path):
    _slice_workspace(tmp_path)
    _rejected(tmp_path, 8, *_acceptance_args(), '--slice-blocker', 'verification pending')


def test_gate_downgrade_requires_reconciling_the_slice_status(tmp_path):
    _slice_workspace(tmp_path)
    assert _second_cli(tmp_path, 8, *_acceptance_args()).returncode == 0
    _rejected(tmp_path, 9, '--gate', 'S00-GATE-01=BLOCKED')
    result = _second_cli(tmp_path, 9, '--gate', 'S00-GATE-01=BLOCKED',
                         '--slice-status', 'BLOCKED', '--slice-blocker', 'evidence invalidated')
    assert result.returncode == 0, result.stderr
    state = json.loads((tmp_path / 'state.json').read_text())
    assert state['slices']['S00']['status'] == 'BLOCKED'
    assert state['slices']['S00']['gates']['S00-GATE-01'] == 'BLOCKED'


def test_advance_cannot_move_backwards(tmp_path):
    _slice_workspace(tmp_path)
    assert _second_cli(tmp_path, 8, *_acceptance_args(), '--advance-to', 'S01').returncode == 0
    _rejected(tmp_path, 9, '--advance-to', 'S00')


def test_missing_source_identity_cannot_support_a_pass_gate(tmp_path):
    state, _, records = workspace(tmp_path)
    path = tmp_path / records[0]['path']
    record = json.loads(path.read_text())
    record.pop('commit_evidence', None)
    path.write_text(json.dumps(record))
    records[0]['record_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    write_index(tmp_path, records)
    _rejected(tmp_path, 7, *PASS_ARGS)


def test_snapshot_seals_require_one_common_source_identity(tmp_path):
    workspace(tmp_path)
    snapshot = {'manifest_path': 'source.json', 'manifest_sha256': 'c' * 64}
    for seal_id in ('S00-GATE-02-TESTS-001', 'S00-GATE-02-EVIDENCE-001'):
        _edit_seal(tmp_path, seal_id, commit_evidence=None, source_snapshot=snapshot)
    result = cli(tmp_path, *PASS_ARGS)
    assert result.returncode == 0, result.stderr
    # Full snapshot provenance remains the readiness validator's responsibility.
    # The helper must still reject a later mixed source identity.
    _edit_seal(tmp_path, 'S00-GATE-02-EVIDENCE-001',
               source_snapshot={**snapshot, 'manifest_sha256': 'd' * 64})
    _rejected(tmp_path, 8, '--gate', 'S00-GATE-02=PASS')


@pytest.mark.parametrize('reconcile', [False, True])
@pytest.mark.parametrize('missing_index', [False, True])
def test_independent_negative_snapshot_acceptance_cannot_rebind_its_commit(tmp_path, reconcile, missing_index):
    """Fresh reviewer chose this negative after inspecting the first correction."""
    records = [write_seal(tmp_path, f'S00-{name}-001', kind, ['S00'])
               for name, kind in [('TESTS', 'TESTS_VERIFIED'), ('EVIDENCE', 'EVIDENCE_VERIFIED'),
                                  ('ACCEPTED', 'SLICE_ACCEPTED')]]
    snapshot = {'manifest_path': 'source.json', 'manifest_sha256': 'c' * 64}
    for indexed in records:
        path = tmp_path / indexed['path']
        record = json.loads(path.read_text())
        record.pop('commit_evidence')
        record['source_snapshot'] = snapshot
        path.write_text(json.dumps(record))
        indexed['record_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    workspace(tmp_path, records)
    arguments = ['--slice-commit', COMMIT, '--resolve-blocker', BLOCKER]
    for gate in ('S00-GATE-01', 'S00-GATE-02'):
        arguments += ['--gate', f'{gate}=PASS', '--gate-seal', f'{gate}=S00-TESTS-001',
                      '--gate-seal', f'{gate}=S00-EVIDENCE-001']
    result = cli(tmp_path, *arguments)
    assert result.returncode == 0, result.stderr
    accepted = _second_cli(tmp_path, 8, *_acceptance_args())
    assert accepted.returncode == 0, accepted.stderr
    rebind = ['--slice', 'S00', '--slice-commit', 'b' * 40]
    if reconcile:
        rebind += ['--slice-status', 'BLOCKED', '--gate', 'S00-GATE-01=BLOCKED',
                   '--gate', 'S00-GATE-02=BLOCKED']
    if missing_index:
        (tmp_path / 'governance/seals/index.json').unlink()
    _rejected(tmp_path, 9, *rebind)


def test_malformed_retained_reference_is_a_typed_rejection(tmp_path):
    state_path, _, _ = workspace(tmp_path)
    state = json.loads(state_path.read_text())
    item = state['slices']['S00']
    item['gates']['S00-GATE-02'] = 'PASS'
    item['commit'] = COMMIT
    item['gate_seal_refs']['S00-GATE-02'] = [{'seal_id': 'S00-GATE-02-TESTS-001'}]
    state_path.write_text(json.dumps(state))
    diagnostic = _rejected(tmp_path, 7, '--slice', 'S00', '--slice-status', 'IN_PROGRESS')
    assert 'Malformed seal reference' in diagnostic
    assert 'Traceback' not in diagnostic


@pytest.mark.parametrize('boundary', ['journal', 'state'])
def test_acceptance_and_advance_recover_together_after_a_write_failure(tmp_path, boundary):
    state_path, ledger_path = _slice_workspace(tmp_path)
    target = (ledger_path.with_name('execution_journal') / 'event-0000000009.json'
              if boundary == 'journal' else state_path)
    # The named boundary fails after its durable write, without a timing race.
    wrapper = (
        'import sys\nfrom pathlib import Path\n'
        f'sys.path.insert(0, {str(SCRIPT.parent)!r})\n'
        'import checkpoint_execution as checkpoint\n'
        'write = checkpoint.write_atomic\n'
        'def fail_after_write(path, data):\n'
        '    write(path, data)\n'
        f'    if Path(path) == Path({str(target)!r}): raise OSError("named acceptance boundary")\n'
        'checkpoint.write_atomic = fail_after_write\n'
        'raise SystemExit(checkpoint.main(sys.argv[1:]))\n'
    )
    result = subprocess.run(
        [str(sys.executable), '-c', wrapper, '--state', str(state_path), '--ledger', str(ledger_path),
         '--seal-root', str(tmp_path), '--seal-index', str(tmp_path / 'governance/seals/index.json'),
         '--expected-revision', '8', '--phase', 'CHECKPOINT', '--next-action', 'resume S01 discovery',
         *_acceptance_args(), '--advance-to', 'S01'],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0
    recovery = _second_cli(tmp_path, 8)
    assert recovery.returncode == 2
    assert 'Recovered pending checkpoint at revision 9' in recovery.stderr
    state = json.loads(state_path.read_text())
    assert state['revision'] == 9
    assert state['current_slice'] == 'S01'
    assert state['slices']['S00']['status'] == 'PASS'
    rows = [json.loads(line) for line in ledger_path.read_text().splitlines()]
    assert [row['revision'] for row in rows] == [8, 9]
    assert rows[-1]['slice_patch']['status'] == 'PASS'
    assert rows[-1]['advance_to'] == 'S01'
