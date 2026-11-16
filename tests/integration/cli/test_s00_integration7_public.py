"""S00 integration step after fix round 7 (LOG-0042 "open for the integration step"): PUBLIC proof.

Every test runs the public CLI in fresh child processes with an isolated ``QUATI_CONFIG_DIR`` /
``QUATI_DATA_DIR`` (proof tier L2). The model, where one is needed, is the SCRIPTED FAKE of
``fixtures/fix7_public_runner.py``: fake-provider compatibility only, never evidence of a real
provider. Boundaries:

* A  - every receipt written under the data directory carries the code digest of the running package
  (audit P2-E; LOG-0041 N4 code-digest binding), on every path including up-front refusals.
* B5 - ``quati trace show`` reports ``result_kind`` for greeting and refused requests (M26 "S00 form
  of show and explain", ``TraceRecord.receipt.result_kind``).
* B6 - ``ask`` and the registry commands give the same typed refusal for an unusable ``capabilities``
  directory (M01 "Data directory" rule 2: ``state_dir_unsafe`` with ``component``).
* D  - an installation whose packaged assets sit inside the package works without the repository
  layout and compiles the same hashes; a missing contract schema is a typed diagnostic.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from test_s00_fix7_public_surface import (  # noqa: F401 - ``profile`` is a fixture
    READ_SCRIPT, REPOSITORY_ROOT, SCRIPTED, WORK_TEXT, Profile, assert_unsafe_state, profile)

GREETING = 'Hello'
HASHES = ('behavior_hash', 'statechart_hash', 'prompt_hash')


def _code_digest(root: Path) -> str:
    """The documented algorithm, recomputed here: sha256 over the sorted (relative path, file sha256) list."""
    entries = sorted((path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest())
                     for path in root.rglob('*.py') if path.is_file())
    return hashlib.sha256(json.dumps(entries, separators=(',', ':')).encode('utf-8')).hexdigest()


def _receipts(profile: Profile) -> list:
    return [json.loads(path.read_bytes()) for path in sorted((profile.data / 'receipts').glob('*.json'))]


def _receipt_of(value: dict) -> dict:
    digest, path = value['evidence_refs'][0].split(':', 2)[1:]
    raw = Path(path).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest
    return json.loads(raw)


# ----------------------------------------------------------------- A: code digest on every receipt
def test_a_every_receipt_written_by_the_public_cli_carries_the_code_digest(profile: Profile) -> None:
    """init, install, probe, greeting, refusals before the model, model-path ask, chat turn, disable, trace."""
    expected = _code_digest(REPOSITORY_ROOT / 'src' / 'quati')
    profile.ready()                                                   # audit_event, capability_command, feature_report
    steps = {
        'greeting': profile.run('ask', GREETING, '--json'),
        'no_provider': profile.run('ask', WORK_TEXT, '--json'),      # NOT_CONFIGURED before any model call
        'unprobed': profile.scripted('ask', WORK_TEXT, '--json', env={'QUATI_MODEL': 'another-model'}),
        'work': profile.scripted('ask', WORK_TEXT, '--json', script=READ_SCRIPT),
        'chat': profile.run('chat', '--jsonl', stdin=(GREETING + '\n').encode()),
        'disable': profile.run('capabilities', 'disable', 'fixtures.calendar-read@1.0.0', '--json'),
    }
    assert [steps[name].code for name in ('greeting', 'no_provider', 'unprobed', 'work', 'disable')] == [0, 3, 4, 0, 0]
    assert steps['unprobed'].value['data']['reason'] == 'MODEL_INCOMPATIBLE'
    assert steps['work'].value['data']['result_kind'] == 'FIXTURE_RESULT'
    shown = profile.run('trace', 'show', steps['greeting'].value['data']['request_id'], '--json')
    assert shown.code == 0 and shown.value['data']['receipt']['digests']['code_digest'] == expected
    receipts = _receipts(profile)
    kinds = sorted(str(receipt.get('kind')) for receipt in receipts)
    assert kinds == ['None'] * 4 + ['ask_receipt', 'audit_event', 'capability_command', 'capability_command',
                                    'feature_report']
    assert [receipt for receipt in receipts if (receipt.get('digests') or {}).get('code_digest') != expected] == []
    for name in ('greeting', 'no_provider', 'unprobed', 'work', 'disable'):
        assert _receipt_of(steps[name].value)['digests']['code_digest'] == expected, name


# ----------------------------------------------------------------- B5: result_kind in every request receipt
def test_b5_trace_show_reports_the_result_kind_of_a_greeting_and_of_a_refused_request(profile: Profile) -> None:
    """M26 TraceRecord.receipt.result_kind for receipts that never reached the model path."""
    profile.ready()
    cases = {'GREETING': profile.run('ask', GREETING, '--json'),
             'BLOCKED': profile.run('ask', WORK_TEXT, '--json')}
    assert (cases['GREETING'].code, cases['BLOCKED'].code) == (0, 3)
    for kind, run in cases.items():
        data = run.value['data']
        assert data['result_kind'] == kind and _receipt_of(run.value)['result_kind'] == kind
        for identifier in (data['request_id'], data['trace_id']):
            shown = profile.run('trace', 'show', identifier, '--json')
            assert (shown.code, shown.value['status']) == (0, 'SUCCEEDED'), shown.out
            assert shown.value['data']['receipt']['result_kind'] == kind
            assert set(shown.value['data']['not_recorded']) == {'commitment_id', 'event_ids'}
            assert shown.value['data']['receipt']['trajectory'] == []
    work = profile.scripted('ask', WORK_TEXT, '--json', script=READ_SCRIPT)
    shown = profile.run('trace', 'show', work.value['data']['request_id'], '--json')
    assert shown.value['data']['receipt']['result_kind'] == 'FIXTURE_RESULT' == _receipt_of(work.value)['result_kind']


def test_b5_a_forged_result_kind_is_withheld_not_displayed(profile: Profile) -> None:
    """The display rule holds for the new field: a value outside the closed list is never shown."""
    assert profile.run('init', '--json').code == 0
    greeting = profile.run('ask', GREETING, '--json')
    path = Path(greeting.value['evidence_refs'][0].split(':', 2)[2])
    record = json.loads(path.read_bytes())
    record['result_kind'] = 'CONVERSATION <script>'
    path.write_bytes(json.dumps(record).encode())
    shown = profile.run('trace', 'show', greeting.value['data']['request_id'], '--json')
    assert (shown.code, shown.value['status']) == (0, 'PARTIAL'), shown.out
    assert shown.value['data']['receipt']['result_kind'] is None
    assert 'receipt_value_withheld:result_kind' in shown.value['uncertainties'] and 'script' not in shown.out


# ----------------------------------------------------------------- B6: one refusal for an unusable capabilities directory
@pytest.mark.parametrize('fault', ['symlink', 'file'])
def test_b6_ask_and_registry_commands_give_the_same_refusal_for_an_unusable_capabilities_directory(
        profile: Profile, fault: str) -> None:
    """M01 "Data directory" rule 2: state_dir_unsafe / component capabilities, before any model call or handler."""
    profile.ready()
    target, moved = profile.data / 'capabilities', profile.root / 'moved'
    target.rename(moved)
    if fault == 'symlink':
        target.symlink_to(moved, target_is_directory=True)
    else:
        target.write_bytes(b'not a directory')
        target.chmod(0o600)
    before = profile.tree(profile.data), profile.tree(moved)
    listed = profile.run('capabilities', 'list', '--json')
    asked = profile.scripted('ask', WORK_TEXT, '--json', script=READ_SCRIPT)
    for run in (listed, asked):
        assert_unsafe_state(run, 'capabilities')
    assert asked.value == listed.value
    assert asked.kinds('request') == [] and asked.kinds('handler') == []
    assert (profile.tree(profile.data), profile.tree(moved)) == before
    chat = profile.run('chat', '--jsonl', env=SCRIPTED, scenario={'script': READ_SCRIPT}, stdin=(WORK_TEXT + '\n').encode())
    turn = json.loads(chat.out.splitlines()[0])
    assert turn['data'] == {'reason': 'state_dir_unsafe', 'component': 'capabilities'} and chat.kinds('request') == []
    # A social-only text uses no registry: its answer does not depend on that directory (LOG-0041 D1).
    greeting = profile.run('ask', GREETING, '--json')
    assert (greeting.code, greeting.value['data']['result_kind']) == (0, 'GREETING')


# ----------------------------------------------------------------- D: packaged assets
def _packaged_copy(site: Path) -> Path:
    """Lay the package out as the wheel does, from pyproject.toml alone: every package directory mapped by
    ``tool.setuptools.package-dir`` and the files its ``package-data`` patterns select."""
    project = tomllib.loads((REPOSITORY_ROOT / 'pyproject.toml').read_text(encoding='utf-8'))['tool']['setuptools']
    shutil.copytree(REPOSITORY_ROOT / 'src' / 'quati', site / 'quati', ignore=shutil.ignore_patterns('__pycache__'))
    for package, source in project['package-dir'].items():
        if not package.startswith('quati.assets'):
            continue
        patterns = project['package-data'][package]
        target = site.joinpath(*package.split('.'))
        target.mkdir(parents=True)
        copied = [shutil.copy2(path, target / path.name)
                  for pattern in patterns for path in sorted((REPOSITORY_ROOT / source).glob(pattern))]
        assert copied, package
    return site


def _child(site: Path, root: Path, *argv: str) -> tuple[int, dict, str]:
    # A copy outside the repository is not the measured source tree: no coverage bootstrap is passed on.
    env = {'PATH': os.environ.get('PATH', ''), 'HOME': str(root / 'home'), 'QUATI_CONFIG_DIR': str(root / 'config'),
           'QUATI_DATA_DIR': str(root / 'data'), 'PYTHONPATH': str(site)}
    work = root / 'cwd'
    work.mkdir(exist_ok=True)
    completed = subprocess.run([sys.executable, '-m', 'quati', *argv], cwd=work, env=env, capture_output=True,
                               text=True, timeout=120, check=False)
    lines = completed.stdout.splitlines()
    assert len(lines) == 1, (completed.stdout, completed.stderr)
    return completed.returncode, json.loads(lines[0]), completed.stderr


def test_d_a_package_with_its_packaged_assets_works_outside_the_repository(tmp_path: Path) -> None:
    """No ``contracts/`` or ``examples/`` beside the package: doctor, init, the greeting and the compiler work,
    and the compiled hashes equal the repository reference (the locator changes no compiled byte)."""
    site = _packaged_copy(tmp_path / 'site')
    assert not (tmp_path / 'contracts').exists() and not (tmp_path / 'examples').exists()
    reference = json.loads((REPOSITORY_ROOT / 'examples' / 'behavior' / 'compiled_receipt.reference.json').read_bytes())
    code, value, err = _child(site, tmp_path, 'doctor', '--json')
    behavior = value['data']['behavior']
    assert (code, value['status'], behavior['status'], err) == (0, 'SUCCEEDED', 'VALID', ''), value
    assert {name: behavior[name] for name in HASHES} == {name: reference[name] for name in HASHES}
    assert behavior['profile_ref'] == 'examples/behavior/executive-secretary.yaml'
    code, value, _ = _child(site, tmp_path, 'init', '--json')
    assert (code, value['data']['policy']['action']) == (0, 'INSTALLED'), value
    code, value, _ = _child(site, tmp_path, 'ask', GREETING, '--json')
    assert (code, value['data']['result_kind']) == (0, 'GREETING'), value
    receipt = json.loads(Path(value['evidence_refs'][0].split(':', 2)[2]).read_bytes())
    assert receipt['digests']['code_digest'] == _code_digest(site / 'quati')      # assets are not code
    code, value, _ = _child(site, tmp_path, 'config', 'validate', '--json')
    checks = {check['name']: check['status'] for check in value['data']['checks']}
    assert (checks['identity'], checks['policy'], checks['behavior']) == ('OK', 'OK', 'OK'), value
    code, value, _ = _child(site, tmp_path, 'behavior', 'validate', 'examples/behavior/executive-secretary.yaml',
                            '--root', str(site / 'quati' / 'assets'), '--json')
    assert code == 0 and value['data']['behavior_hash'] == reference['behavior_hash']


def test_d_missing_contract_schemas_are_a_typed_diagnostic_never_an_internal_error(tmp_path: Path) -> None:
    """A copy with the examples but without ``contracts/``: doctor still reports, and names what is missing."""
    site = tmp_path / 'layout' / 'src'
    shutil.copytree(REPOSITORY_ROOT / 'src' / 'quati', site / 'quati', ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(REPOSITORY_ROOT / 'examples', tmp_path / 'layout' / 'examples')
    code, value, err = _child(site, tmp_path, 'doctor', '--json')
    behavior = value['data']['behavior']
    assert (code, value['status'], value['error'], err) == (0, 'SUCCEEDED', None, ''), (value, err)
    assert behavior['status'] == 'INVALID' and 'behavior_package_invalid' in value['data']['warnings']
    assert [(item['code'], item['reason']) for item in behavior['diagnostics']] == [('NOT_FOUND', 'CONTRACT_NOT_FOUND')]
    assert behavior['diagnostics'][0]['path'].startswith('contracts/') and str(tmp_path) not in json.dumps(behavior)
    code, value, err = _child(site, tmp_path, 'config', 'validate', '--json')
    assert (code, value['error']['code']) == (2, 'CONFIG_INVALID') and 'internal error' not in err
