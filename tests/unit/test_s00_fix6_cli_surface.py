"""S00 fix round 6: public CLI surface corrections from the independent gate audit (LOG-0039).

Findings covered here (docs/audit/S00_GATES_01_03_04_AUDIT_2026-11-16.md): F6 probes authenticate
before any provider call or write (IDN-01, M02 authorization order, M17 probe command); F7 the
registry audit log is a private no-follow file and the data directories are owner-only (M26
``audit_unavailable``, K7); F8 M17-RT-02 on the public path; F9 an invalid active behavior package
is a typed ``CONFIG_INVALID`` in ``ask`` and visible in ``doctor`` (M30-FR-02, CMP-02); F10 the M01
``DoctorReport`` fields; F11 the key canary; F12 the M01 command table (M01-FR-01).

Every test calls the public entry ``quati.cli.main.main``. Proof tier: L1/L2 (deterministic). The
model is the SCRIPTED FAKE provider of ``s00_t04_support``: fake-provider compatibility only, never
evidence of a real provider. No network, no vendor executable, no live allowance variable.
"""

from __future__ import annotations

import io
import json
import os
import platform
import shutil
import socket
import sqlite3
import stat
import sys
from pathlib import Path

import pytest

from s00_t04_support import (
    FAKE_TRANSPORT, FakeClock, Script, ScriptedFakeProvider, classified, describe, final, invoke, search)

from quati.adapters import private_fs, runtime_facts
from quati.adapters.capability_store import FileRegistryStore
from quati.application import behavior_commands, providers
from quati.application.ask import ask_probe_profile
from quati.application.cli_service import CLIService
from quati.application.identity import AccessDenied
from quati.application.ports import ProviderConfig
from quati.behavior.compiler import BehaviorCompiler
from quati.cli import composition, rendering
from quati.cli import main as cli_main
from quati.domain.capability_registry import Refusal

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PROVIDER_VARIABLES = ('QUATI_BASE_URL', 'QUATI_MODEL', 'QUATI_ALLOW_LIVE', 'QUATI_API_KEY_ENV', 'QUATI_API_KEY',
                      'QUATI_PROVIDER', 'QUATI_CAPABILITY_CONTEXT', 'QUATI_LIVE_EVAL')
CANARY = 'sk-quati-canary-7f3a9c41d2e84b06a5c1-NEVER-PRINT'
RESPONSE_KEYS = {'status', 'data', 'evidence_refs', 'uncertainties', 'next_action', 'error'}
WORK_TEXT = 'Find my next appointment'


def read_script(query: str = 'next appointment calendar', answer: str = 'done') -> list:
    return [classified(), search(query), describe('fixtures.calendar-read'),
            invoke('fixtures.calendar-read', limit=1), final(answer)]


class Cli:
    """One isolated LOCAL profile driven through ``main`` in this process."""

    def __init__(self, root: Path, monkeypatch, capsys) -> None:
        self.root, self.monkeypatch, self.capsys = root, monkeypatch, capsys
        self.config, self.data = root / 'config', root / 'data'
        self.script: Script | None = None
        self.outputs: list[str] = []

    def run(self, *argv: str, stdin: bytes | None = None):
        if stdin is not None:
            self.monkeypatch.setattr(sys, 'stdin', io.TextIOWrapper(io.BytesIO(stdin), encoding='utf-8'))
        code = cli_main.main(list(argv))
        captured = self.capsys.readouterr()
        self.outputs += [captured.out, captured.err]
        return code, captured.out, captured.err

    def one(self, *argv: str):
        code, out, err = self.run(*argv)
        lines = out.splitlines()
        assert len(lines) == 1, (out, err)               # M01-FR-01: exactly one Response object on stdout
        value = json.loads(lines[0])
        assert set(value) == RESPONSE_KEYS
        return code, value, err

    def scripted(self, *items, **config) -> Script:
        """Attach the SCRIPTED FAKE transport; the configuration is injected, no environment variable is set."""
        providers.transports()
        self.monkeypatch.setitem(providers._REGISTRY, FAKE_TRANSPORT, ScriptedFakeProvider)
        self.script = Script(*items)
        self.monkeypatch.setattr(ScriptedFakeProvider, 'active_script', self.script)
        self.monkeypatch.setattr(cli_main, '_config',
                                 lambda: ProviderConfig(transport=FAKE_TRANSPORT, allow_live=True, **config))
        return self.script

    def files(self) -> dict:
        return {str(path.relative_to(self.root)): path.read_bytes()
                for base in (self.config, self.data) if base.exists()
                for path in sorted(base.rglob('*')) if path.is_file() and not path.is_symlink()}

    def ready(self, *items) -> Script:
        """Initialized profile, calendar-read enabled and a successful scripted probe."""
        script = self.scripted(*items)
        assert self.one('init', '--json')[0] == 0
        assert self.one('capabilities', 'install-fixture', 'calendar-read', '--enable-fixture', '--json')[0] == 0
        code, value, _ = self.one('models', 'probe', '--json')
        assert (code, value['status']) == (0, 'SUCCEEDED'), value
        return script


@pytest.fixture
def cli(tmp_path, monkeypatch, capsys) -> Cli:
    for name in PROVIDER_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('QUATI_CONFIG_DIR', str(tmp_path / 'config'))
    monkeypatch.setenv('QUATI_DATA_DIR', str(tmp_path / 'data'))
    return Cli(tmp_path, monkeypatch, capsys)


def assert_unauthenticated(code: int, value: dict) -> None:
    assert (code, value['status'], value['error']['code'], value['data']) == (4, 'DENIED', 'UNAUTHENTICATED', None)


# ----------------------------------------------------------------- F6: probes authenticate first
@pytest.mark.parametrize('argv', [('models', 'probe', '--json'), ('doctor', '--probe', '--json')])
def test_f6_probe_without_identity_is_denied_before_any_provider_call_or_write(cli: Cli, argv) -> None:
    """IDN-01 / M02 order row 1: no local credential -> UNAUTHENTICATED, zero model calls, nothing written."""
    script = cli.scripted()
    code, value, _ = cli.one(*argv)
    assert_unauthenticated(code, value)
    assert script.requests == []
    assert cli.files() == {} and not (cli.data / 'receipts').exists() and not (cli.data / 'feature_reports').exists()


@pytest.mark.parametrize('argv', [('models', 'probe', '--json'), ('doctor', '--probe', '--json')])
def test_f6_probe_in_a_capability_context_is_denied_and_changes_nothing(cli: Cli, argv) -> None:
    """The capability-invocation marker closes the human CLI path for probes as it does for ask."""
    script = cli.scripted()
    assert cli.one('init', '--json')[0] == 0
    before = cli.files()
    cli.monkeypatch.setenv('QUATI_CAPABILITY_CONTEXT', '1')
    code, value, _ = cli.one(*argv)
    assert_unauthenticated(code, value)
    assert script.requests == [] and cli.files() == before


def test_f6_an_authenticated_probe_still_measures_and_plain_doctor_needs_no_identity(cli: Cli) -> None:
    """Controls: plain doctor stays usable with no identity (M01-AT-01); a probe after init works."""
    script = cli.scripted()
    code, value, _ = cli.one('doctor', '--json')
    assert (code, value['status'], value['data']['identity']['initialized']) == (0, 'SUCCEEDED', False)
    assert script.requests == [] and cli.files() == {}
    assert cli.one('init', '--json')[0] == 0
    code, value, _ = cli.one('doctor', '--probe', '--json')
    assert (code, value['status'], value['data']['provider']['status']) == (0, 'SUCCEEDED', 'PROBED')
    assert script.requests and any(name.startswith('data/feature_reports/') for name in cli.files())


# ----------------------------------------------------------------- F7: private audit log and data directories
def test_f7_data_directories_and_files_are_created_owner_only(cli: Cli) -> None:
    """``data/``, ``data/capabilities/`` and what the registry and the evidence sink write are 0700 / 0600."""
    previous = os.umask(0o002)                       # a permissive umask must not widen any created path
    try:
        cli.ready(*read_script())
        code, value, _ = cli.one('ask', WORK_TEXT, '--json')
        assert (code, value['data']['result_kind']) == (0, 'FIXTURE_RESULT'), value
    finally:
        os.umask(previous)
    checked = [cli.data, *(path for name in ('capabilities', 'receipts', 'feature_reports')
                           for path in [cli.data / name, *sorted((cli.data / name).rglob('*'))])]
    assert cli.data / 'capabilities' / 'audit.jsonl' in checked
    wrong = [(str(path.relative_to(cli.root)), oct(stat.S_IMODE(path.lstat().st_mode))) for path in checked
             if stat.S_IMODE(path.lstat().st_mode) != (0o700 if path.is_dir() else 0o600)]
    assert wrong == []


def _audit_fault(cli: Cli, fault: str) -> Path:
    """Replace the audit log by an unsafe one; return the file that must stay byte-identical."""
    log = cli.data / 'capabilities' / 'audit.jsonl'
    victim = cli.root / 'victim.txt'
    victim.write_bytes(b'victim\n')
    if fault == 'symlink':
        log.unlink()
        log.symlink_to(victim)
    elif fault == 'dangling_symlink':
        victim.unlink()
        log.unlink()
        log.symlink_to(victim)
    elif fault == 'group_writable':
        log.chmod(0o660)
        return log
    elif fault == 'world_readable':
        log.chmod(0o644)
        return log
    return victim


@pytest.mark.parametrize('fault', ['symlink', 'dangling_symlink', 'group_writable', 'world_readable'])
def test_f7_an_unsafe_audit_log_refuses_the_read_and_writes_nowhere_else(cli: Cli, fault: str) -> None:
    """K7 / M26 ``audit_unavailable``: a symlinked or insecure audit log fails closed; no handler runs."""
    cli.ready(*read_script())
    guarded = _audit_fault(cli, fault)
    before = guarded.read_bytes() if guarded.exists() else None
    code, value, _ = cli.one('ask', WORK_TEXT, '--json')
    assert (code, value['status'], value['error']['code']) == (5, 'UNAVAILABLE', 'TEMPORARILY_UNAVAILABLE'), value
    assert value['data']['reason'] == 'audit_unavailable' and value['data']['result_kind'] == 'BLOCKED'
    assert value['data']['tool_calls'] and not any(call['handler_executed'] for call in value['data']['tool_calls'])
    assert (guarded.read_bytes() if guarded.exists() else None) == before


@pytest.mark.parametrize('fault', ['symlink', 'group_writable'])
def test_f7_an_unsafe_audit_log_refuses_a_registry_write_with_the_typed_reason(cli: Cli, fault: str) -> None:
    cli.ready()
    guarded = _audit_fault(cli, fault)
    before = guarded.read_bytes()
    code, value, err = cli.one('capabilities', 'install-fixture', 'mail-search', '--enable-fixture', '--json')
    assert (code, value['status'], value['error']['code']) == (5, 'UNAVAILABLE', 'TEMPORARILY_UNAVAILABLE'), value
    assert value['data'] == {'reason': 'audit_unavailable'} and 'internal error' not in err
    assert guarded.read_bytes() == before
    # With a private log again, the registry shows that the refused install changed nothing.
    log = cli.data / 'capabilities' / 'audit.jsonl'
    if log.is_symlink():
        log.unlink()
    else:
        log.chmod(0o600)
    code, value, _ = cli.one('capabilities', 'list', '--json')
    assert code == 0 and [item['capability_id'] for item in value['data']['capabilities']] == ['fixtures.calendar-read']


def test_f7_a_symlinked_registry_directory_is_refused(cli: Cli) -> None:
    cli.ready(*read_script())
    real = cli.data / 'capabilities'
    moved = cli.root / 'elsewhere'
    real.rename(moved)
    real.symlink_to(moved, target_is_directory=True)
    before = (moved / 'audit.jsonl').read_bytes()
    code, value, _ = cli.one('ask', WORK_TEXT, '--json')
    assert code != 0 and value['status'] != 'SUCCEEDED'
    assert not any(call['handler_executed'] for call in (value['data'] or {}).get('tool_calls', []))
    assert (moved / 'audit.jsonl').read_bytes() == before


# ----------------------------------------------------------------- F8: M17-RT-02 on the public path
SESSION_FILE = json.dumps({'OPENAI_API_KEY': None, 'tokens': {
    'id_token': 'eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ4In0.c2lnQ0FOQVJZ', 'access_token': 'eyJhbGciOiJSUzI1NiJ9.e30.c2ln',
    'refresh_token': 'rt_CANARY0123456789', 'account_id': 'acc'}, 'last_refresh': '2026-11-01T00:00:00Z'})


@pytest.mark.parametrize('value', [SESSION_FILE, 'eyJhbGciOiJSUzI1NiJ9.eyJhdWQiOiJjaGF0Z3B0In0.c2lnQ0FOQVJZ',
                                   '~/.codex/auth.json'])
def test_f8_a_sign_in_session_artifact_is_not_a_key_on_the_public_path(cli: Cli, value: str) -> None:
    """M17-RT-02: session-file content and session tokens are API_KEY_REF_INVALID; the value is never shown."""
    cli.monkeypatch.setenv('QUATI_PROVIDER', 'openai_compatible')
    cli.monkeypatch.setenv('QUATI_BASE_URL', 'https://api.openai.com/v1')
    cli.monkeypatch.setenv('QUATI_MODEL', 'gpt-tools-pro')
    cli.monkeypatch.setenv('QUATI_API_KEY_ENV', 'CODEX_SESSION')
    cli.monkeypatch.setenv('CODEX_SESSION', value)
    assert cli.one('init', '--json')[0] == 0
    code, doctor, _ = cli.one('doctor', '--json')
    assert code == 0 and doctor['data']['provider']['reasons'][0] == 'API_KEY_REF_INVALID'
    assert doctor['data']['provider']['status'] == 'NOT_CONFIGURED'
    code, probe, _ = cli.one('models', 'probe', '--json')
    assert (code, probe['status'], probe['error']['code']) == (3, 'BLOCKED', 'NOT_CONFIGURED')
    assert probe['data']['provider']['reasons'][0] == 'API_KEY_REF_INVALID'
    for text in (*cli.outputs, *(blob.decode('utf-8', 'replace') for blob in cli.files().values())):
        assert value not in text and 'c2lnQ0FOQVJZ' not in text and 'rt_CANARY' not in text


# ----------------------------------------------------------------- F9: invalid active behavior package
def _behavior_tree(cli: Cli, old: str | None = None, new: str | None = None) -> Path:
    """A copy of the shipped behavior package made the active one; optionally with one edited statechart line."""
    tree = cli.root / 'tree'
    for name in ('behavior', 'statecharts'):
        shutil.copytree(REPOSITORY_ROOT / 'examples' / name, tree / 'examples' / name)
    if old is not None:
        chart = tree / 'examples' / 'statecharts' / 'commitment.yaml'
        text = chart.read_text(encoding='utf-8')
        assert text.count(old) == 1
        chart.write_text(text.replace(old, new), encoding='utf-8')
    cli.monkeypatch.setattr(composition, 'REPOSITORY_ROOT', tree)
    return tree


@pytest.mark.parametrize(('old', 'new', 'expected'), [
    ('guard: authorized_request, action: commit_receipt', 'guard: always, action: commit_receipt',
     ('FORBIDDEN', 'transitions[')),
    ('guard: safe_to_begin, action: start_work', 'guard: allow_anything, action: shell_exec',
     ('UNSUPPORTED', 'transitions[3].guard')),
])
def test_f9_ask_and_doctor_name_the_invalid_statechart_path(cli: Cli, old, new, expected) -> None:
    """CMP-02 on the only S00 runtime path: a typed CONFIG_INVALID with the compiler's path, never INTERNAL_ERROR."""
    script = cli.ready(*read_script())
    _behavior_tree(cli, old, new)
    asked = len(script.model_requests())
    code, value, err = cli.one('ask', WORK_TEXT, '--json')
    assert (code, value['status'], value['error']['code']) == (2, 'BLOCKED', 'CONFIG_INVALID'), value
    assert 'internal error' not in err
    data = value['data']
    assert data['reason'] == 'BEHAVIOR_PACKAGE_INVALID' and data['result_kind'] == 'BLOCKED'
    assert (data['received'], data['launched'], data['delivered']) == (True, False, False)
    found = [(item['code'], item['path']) for item in data['diagnostics']]
    assert any(code_ == expected[0] and path.startswith(expected[1]) for code_, path in found), found
    assert value['uncertainties'] and expected[1] in ' '.join(value['uncertainties'])
    assert len(script.model_requests()) == asked            # refused before any model call
    assert value['evidence_refs']                           # the refusal is receipted like any blocked ask
    code, doctor, _ = cli.one('doctor', '--json')
    behavior = doctor['data']['behavior']
    assert code == 0 and behavior['status'] == 'INVALID' and behavior['profile_ref'] == composition.BEHAVIOR_PROFILE
    assert [(item['code'], item['path']) for item in behavior['diagnostics']] == found
    assert 'behavior_package_invalid' in doctor['data']['warnings'] and doctor['data']['config_valid'] is False
    code, greeting, _ = cli.one('ask', 'hello', '--json')
    assert (code, greeting['data']['result_kind']) == (0, 'GREETING')


def test_f9_doctor_reports_the_valid_active_package_hashes(cli: Cli) -> None:
    tree = _behavior_tree(cli)
    receipt = BehaviorCompiler(tree).compile(composition.BEHAVIOR_PROFILE).receipt
    code, value, _ = cli.one('doctor', '--json')
    behavior = value['data']['behavior']
    assert code == 0 and behavior['status'] == 'VALID' and behavior['diagnostics'] == []
    assert {name: behavior[name] for name in ('behavior_hash', 'statechart_hash', 'prompt_hash')} == {
        name: receipt[name] for name in ('behavior_hash', 'statechart_hash', 'prompt_hash')}
    assert 'behavior_package_invalid' not in value['data']['warnings']


# ----------------------------------------------------------------- F10: M01 DoctorReport
def test_f10_doctor_report_carries_the_m01_fields_before_init(cli: Cli) -> None:
    code, value, _ = cli.one('doctor', '--json')
    data = value['data']
    assert code == 0 and value['status'] == 'SUCCEEDED'
    assert data['profile'] == 'LOCAL' and data['os'] == platform.system()
    assert data['os_qualification'] == ('QUALIFIED' if platform.system() == 'Linux' else 'NOT_VERIFIED')
    assert data['python_version'] == platform.python_version()
    assert data['sqlite_version'] == sqlite3.sqlite_version
    assert isinstance(data['sqlite_fts5'], bool) and data['sqlite_ok'] is data['sqlite_fts5']
    # S00 has no ledger database, so the journal mode is not measured: the explicit not-verified value.
    assert (data['sqlite_journal_mode'], data['sqlite_journal_reason']) == ('NOT_VERIFIED', 'ledger_not_delivered')
    assert data['config_dir'] is None                 # no profile path for an unauthenticated caller (IDN-01)
    assert data['live_calls_allowed'] is False and data['listening_sockets'] == 0
    assert data['worker'] == {'status': 'NOT_APPLICABLE', 'reason': 'worker_not_delivered'}
    provider = data['provider']
    assert (provider['status'], provider['measured_support']) == ('NOT_CONFIGURED', 'NOT_VERIFIED')
    assert data['policy'] == {'status': 'UNAVAILABLE', 'reason': 'missing'}
    assert isinstance(data['warnings'], list) and 'identity_not_initialized' in data['warnings']
    assert isinstance(data['config_valid'], bool)
    assert cli.files() == {}


def test_f10_listening_sockets_and_the_live_allowance_are_measured_not_constants(cli: Cli) -> None:
    cli.scripted()                                    # injected configuration with the live allowance on
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)
        code, value, _ = cli.one('doctor', '--json')
    assert code == 0 and value['data']['listening_sockets'] == 1 and value['data']['live_calls_allowed'] is True
    assert 'listening_socket_open' in value['data']['warnings']
    assert cli.one('doctor', '--json')[1]['data']['listening_sockets'] == 0


def test_f10_plain_doctor_shows_the_measured_verdicts_of_the_stored_report(cli: Cli) -> None:
    """After a successful probe, doctor reports the measured support for this exact configuration only."""
    cli.scripted()
    assert cli.one('init', '--json')[0] == 0
    before = cli.one('doctor', '--json')[1]['data']['provider']
    assert (before['status'], before['measured_support'], set(before['features'].values())) == (
        'NOT_PROBED', 'NOT_VERIFIED', {'NOT_VERIFIED'})
    code, probe, _ = cli.one('models', 'probe', '--json')
    assert code == 0
    files = cli.files()
    after = cli.one('doctor', '--json')[1]['data']['provider']
    assert (after['status'], after['measured_support']) == ('PROBED', 'SUPPORTED')
    assert after['features'] == probe['data']['feature_report']['features']
    assert after['feature_report']['ref'] == probe['evidence_refs'][0]
    assert after['feature_report']['measured_at'] == probe['data']['feature_report']['measured_at']
    assert cli.files() == files                       # plain doctor is read-only
    # Another configuration has another config hash: its support is not measured.
    cli.scripted(max_requests=11)
    other = cli.one('doctor', '--json')[1]['data']['provider']
    assert (other['status'], other['measured_support'], set(other['features'].values())) == (
        'NOT_PROBED', 'NOT_VERIFIED', {'NOT_VERIFIED'})
    # Without an authenticated identity the stored measurement is not read at all.
    cli.scripted()
    (cli.config / 'device.key').unlink()
    anonymous = cli.one('doctor', '--json')[1]['data']['provider']
    assert (anonymous['status'], anonymous['measured_support']) == ('NOT_PROBED', 'NOT_VERIFIED')
    assert 'feature_report' not in anonymous


def test_f10_a_probe_that_did_not_open_the_ask_gate_is_not_reported_as_supported(cli: Cli) -> None:
    script = cli.scripted()
    script.probe_tools = 'wrong'                      # a completed exchange that contradicts tool support
    assert cli.one('init', '--json')[0] == 0
    code, probe, _ = cli.one('models', 'probe', '--json')
    assert (code, probe['status']) == (0, 'PARTIAL')
    provider = cli.one('doctor', '--json')[1]['data']['provider']
    assert (provider['status'], provider['measured_support'], provider['features']['tools']) == (
        'PROBED', 'NOT_VERIFIED', 'UNSUPPORTED')


# ----------------------------------------------------------------- F11: the key canary
def _assert_no_canary(cli: Cli) -> None:
    for text in cli.outputs:
        assert CANARY not in text
    leaked = [name for name, blob in cli.files().items() if CANARY.encode() in blob]
    assert leaked == []


def test_f11_canary_key_is_absent_from_every_output_of_an_api_transport(cli: Cli) -> None:
    """GATE-01: with the key set, doctor, both probes, ask and chat never print or store its value."""
    cli.monkeypatch.setenv('QUATI_API_KEY_ENV', 'QUATI_CANARY_KEY')
    cli.monkeypatch.setenv('QUATI_CANARY_KEY', CANARY)
    cli.monkeypatch.setenv('QUATI_PROVIDER', 'openai_compatible')
    cli.monkeypatch.setenv('QUATI_BASE_URL', 'https://models.invalid/v1')
    cli.monkeypatch.setenv('QUATI_MODEL', 'synthetic-model')
    assert cli.one('init', '--json')[0] == 0
    code, doctor, _ = cli.one('doctor', '--json')
    reasons = doctor['data']['provider']['reasons']
    assert code == 0 and reasons[0] == 'LIVE_NOT_ALLOWED'                              # the key itself was accepted
    assert not {'API_KEY_MISSING', 'API_KEY_REF_INVALID'} & set(reasons)
    assert cli.one('doctor', '--probe', '--json')[0] == 3
    assert cli.one('models', 'probe', '--json')[0] == 3
    assert cli.one('ask', WORK_TEXT, '--json')[0] == 3
    assert cli.one('ask', f'hello {CANARY}', '--json')[0] in (0, 3)
    assert cli.run('doctor')[0] == 0                                                   # human rendering too
    code, out, _ = cli.run('chat', '--jsonl', stdin=f'Hello\n{WORK_TEXT} {CANARY}\n/help\n/quit\n'.encode())
    assert code == 0 and len(out.splitlines()) == 4
    assert cli.one('config', 'validate', '--json')[0] == 0
    _assert_no_canary(cli)


def test_f11_use_case_results_hold_no_key_value_before_the_output_redactor(cli: Cli) -> None:
    """Defense in depth: the use cases never put the key in a Response; the redactor is only the second layer."""
    cli.monkeypatch.setenv('QUATI_API_KEY_ENV', 'QUATI_CANARY_KEY')
    cli.monkeypatch.setenv('QUATI_CANARY_KEY', CANARY)
    cli.monkeypatch.setenv('QUATI_PROVIDER', 'openai_compatible')
    cli.monkeypatch.setenv('QUATI_BASE_URL', 'https://models.invalid/v1')
    cli.monkeypatch.setenv('QUATI_MODEL', 'synthetic-model')
    assert cli.one('init', '--json')[0] == 0
    service = cli_main._service()
    raw = [service.doctor(), service.doctor(probe=True), service.probe(), service.config_validate(),
           service.ask(WORK_TEXT), service.ask('hello')]
    assert [code for code, _ in raw] == [0, 3, 3, 0, 3, 0]
    assert CANARY not in json.dumps(raw)
    assert raw[0][1]['data']['provider']['reasons'][0] == 'LIVE_NOT_ALLOWED'


def test_f11_canary_key_is_absent_from_receipts_reports_and_the_audit_log_of_a_probed_session(cli: Cli) -> None:
    """A scripted model and a requester that both repeat the key cannot get it into any stored file."""
    cli.monkeypatch.setenv('QUATI_API_KEY_ENV', 'QUATI_CANARY_KEY')
    cli.monkeypatch.setenv('QUATI_CANARY_KEY', CANARY)
    script = cli.ready()
    assert cli.one('doctor', '--probe', '--json')[0] == 0
    assert cli.one('doctor', '--json')[1]['data']['provider']['status'] == 'PROBED'
    script.add(*read_script(f'next appointment calendar {CANARY}', f'The key is {CANARY}'))
    code, value, _ = cli.one('ask', f'{WORK_TEXT} {CANARY}', '--json', '--synthetic-evidence')
    assert code == 0 and value['data']['result_kind'] == 'FIXTURE_RESULT', value
    script.add(*read_script(f'calendar {CANARY}', CANARY))
    code, out, _ = cli.run('chat', '--jsonl', stdin=f'{WORK_TEXT} {CANARY}\n/quit\n'.encode())
    assert code == 0 and len(out.splitlines()) == 2
    names = set(cli.files())
    assert 'data/capabilities/audit.jsonl' in names
    assert any(name.startswith('data/receipts/') for name in names)
    assert any(name.startswith('data/feature_reports/') for name in names)
    _assert_no_canary(cli)


# ----------------------------------------------------------------- F12: the M01 command table
UNDELIVERED = [
    (('inbox',), 'S02'), (('inbox', '--unread'), 'S02'), (('inbox', '--ack', 'msg-1'), 'S02'), (('messages',), 'S02'),
    (('worker', 'run'), 'S02'), (('worker', 'tick'), 'S02'), (('worker', 'install'), 'S02'),
    (('worker', 'uninstall'), 'S02'),
    (('config', 'diff'), 'S03'), (('config', 'simulate'), 'S03'), (('config', 'propose'), 'S03'),
    (('config', 'apply'), 'S03'), (('config', 'rollback'), 'S03'), (('config', 'validate', 'profile.toml'), 'S03'),
    (('trace', 'show', 'c-1'), 'S02'), (('trace', 'show', '--request', 'request-1'), 'S02'),
    (('trace', 'explain', 'c-1'), 'S02'), (('trace', 'export', 'trace-1', '--out', 'trace.json'), 'S02'),
    (('trace', 'replay', 'trace-1'), 'S02'),
    (('behavior', 'propose', 'package.yaml'), 'S03'), (('behavior', 'simulate', 'package.yaml'), 'S03'),
    (('behavior', 'diff', 'a', 'b'), 'S03'), (('behavior', 'promote', 'digest', '--approval', 'apr-1'), 'S03'),
    (('behavior', 'rollback', 'executive-secretary', 'digest'), 'S03'),
]


@pytest.mark.parametrize(('argv', 'slice_id'), UNDELIVERED, ids=[' '.join(argv) for argv, _ in UNDELIVERED])
def test_f12_undelivered_commands_are_registered_and_typed_unsupported(cli: Cli, argv, slice_id) -> None:
    """M01-FR-01: a command whose slice is not delivered returns UNSUPPORTED naming that slice, never INVALID_INPUT."""
    code, value, err = cli.one(*argv, '--json')
    assert (code, value['status'], value['error']['code'], value['data']) == (4, 'UNAVAILABLE', 'UNSUPPORTED', None)
    assert f'slice {slice_id}' in value['error']['message'] and slice_id in value['next_action']
    assert err == '' and cli.files() == {} and not (cli.root / 'trace.json').exists()


def test_f12_help_lists_every_command_of_the_m01_table(cli: Cli) -> None:
    code, out, _ = cli.run('--help')
    assert code == 0
    for command in ('doctor', 'ask', 'tell', 'status', 'inbox', 'messages', 'config', 'worker', 'trace', 'chat',
                    'behavior', 'models', 'capabilities'):
        assert f' {command} ' in out, command


def test_f12_config_validate_reports_each_configuration_check(cli: Cli) -> None:
    """``config validate`` runs the existing configuration checks read-only and needs no identity."""
    code, value, _ = cli.one('config', 'validate', '--json')
    checks = {item['name']: item for item in value['data']['checks']}
    assert (code, value['status'], value['data']['valid']) == (0, 'PARTIAL', True)
    assert list(checks) == ['identity', 'policy', 'provider', 'behavior']
    assert checks['identity']['status'] == 'NOT_CONFIGURED' and checks['policy']['status'] == 'NOT_CONFIGURED'
    assert checks['provider']['status'] == 'NOT_CONFIGURED'
    assert checks['provider']['reasons'][:2] == ['API_KEY_MISSING', 'LIVE_NOT_ALLOWED']
    assert checks['behavior'] == {'name': 'behavior', 'status': 'OK', 'reasons': []}
    assert value['data']['config_dir'] is None
    assert value['uncertainties'] == ['identity: NOT_CONFIGURED', 'policy: NOT_CONFIGURED', 'provider: NOT_CONFIGURED']
    assert cli.files() == {}
    assert cli.one('init', '--json')[0] == 0
    files = cli.files()
    cli.scripted()
    code, value, _ = cli.one('config', 'validate', '--json')
    assert (code, value['status'], value['data']['valid'], value['uncertainties']) == (0, 'SUCCEEDED', True, [])
    assert {item['status'] for item in value['data']['checks']} == {'OK'}
    assert value['data']['config_dir'] == str(cli.config)
    assert cli.one('doctor', '--json')[1]['data']['config_dir'] == str(cli.config)
    assert cli.files() == files


def test_f12_config_validate_rejects_present_but_invalid_configuration(cli: Cli) -> None:
    assert cli.one('init', '--json')[0] == 0
    cli.scripted()
    (cli.config / 'policy.json').chmod(0o644)
    code, value, _ = cli.one('config', 'validate', '--json')
    checks = {item['name']: item for item in value['data']['checks']}
    assert (code, value['status'], value['error']['code'], value['data']['valid']) == (
        2, 'DENIED', 'CONFIG_INVALID', False)
    assert checks['policy'] == {'name': 'policy', 'status': 'INVALID', 'reasons': ['wrong_mode']}
    assert value['uncertainties'] == ['policy: INVALID (wrong_mode)']
    (cli.config / 'policy.json').chmod(0o600)
    cli.monkeypatch.setattr(cli_main, '_config', ProviderConfig.from_environment)
    cli.monkeypatch.setenv('QUATI_PROVIDER', 'no-such-transport')
    code, value, _ = cli.one('config', 'validate', '--json')
    checks = {item['name']: item for item in value['data']['checks']}
    assert (code, value['error']['code']) == (2, 'CONFIG_INVALID')
    assert checks['provider'] == {'name': 'provider', 'status': 'INVALID', 'reasons': ['TRANSPORT_UNKNOWN']}
    cli.monkeypatch.delenv('QUATI_PROVIDER')
    _behavior_tree(cli, 'guard: safe_to_begin, action: start_work', 'guard: allow_anything, action: shell_exec')
    code, value, _ = cli.one('config', 'validate', '--json')
    checks = {item['name']: item for item in value['data']['checks']}
    assert (code, value['error']['code'], checks['behavior']['status']) == (2, 'CONFIG_INVALID', 'INVALID')
    assert any('transitions[3].guard' in reason for reason in checks['behavior']['reasons'])


# ----------------------------------------------------------------- unit edges of the new adapters and use cases
def test_private_directory_creates_tightens_and_refuses(tmp_path, monkeypatch) -> None:
    """F7: the owner-only rule of the state directories (deterministic unit edges of the same guard)."""
    previous = os.umask(0o002)
    try:
        created = private_fs.private_directory(tmp_path / 'a' / 'b' / 'c')
    finally:
        os.umask(previous)
    assert [stat.S_IMODE((tmp_path / name).stat().st_mode) for name in ('a', 'a/b', 'a/b/c')] == [0o700] * 3
    created.chmod(0o775)
    assert stat.S_IMODE(private_fs.private_directory(created).stat().st_mode) == 0o700
    (tmp_path / 'file').write_bytes(b'x')
    (tmp_path / 'link').symlink_to(created, target_is_directory=True)
    for unsafe in (tmp_path / 'file', tmp_path / 'link'):
        with pytest.raises(PermissionError):
            private_fs.private_directory(unsafe)
    assert stat.S_IMODE(created.stat().st_mode) == 0o700
    # A directory another process created between the existence check and mkdir is checked, not trusted.
    raced = tmp_path / 'raced'
    real_mkdir = os.mkdir

    def racing_mkdir(path, mode=0o777):
        real_mkdir(path, 0o777)
        raise FileExistsError(path)

    monkeypatch.setattr(private_fs.os, 'mkdir', racing_mkdir)
    assert stat.S_IMODE(private_fs.private_directory(raced).stat().st_mode) == 0o700
    monkeypatch.setattr(private_fs.os, 'getuid', lambda: os.geteuid() + 1)
    with pytest.raises(PermissionError):
        private_fs.private_directory(created)


def test_private_files_are_no_follow_singly_linked_and_owner_only(tmp_path, monkeypatch) -> None:
    target = tmp_path / 'log'
    descriptor = private_fs.open_private(target, os.O_WRONLY | os.O_APPEND)
    os.write(descriptor, b'one\n')
    os.close(descriptor)
    assert stat.S_IMODE(target.stat().st_mode) == 0o600 and private_fs.read_private(target) == b'one\n'
    assert private_fs.read_private(tmp_path / 'absent') is None
    private_fs.write_private(tmp_path / 'new', b'data')
    assert (tmp_path / 'new').read_bytes() == b'data' and stat.S_IMODE((tmp_path / 'new').stat().st_mode) == 0o600
    with pytest.raises(FileExistsError):
        private_fs.write_private(tmp_path / 'new', b'again')
    (tmp_path / 'link').symlink_to(target)
    (tmp_path / 'directory').mkdir()
    os.link(target, tmp_path / 'hard')
    for unsafe in (tmp_path / 'link', tmp_path / 'directory', tmp_path / 'hard'):
        with pytest.raises(OSError):
            private_fs.read_private(unsafe)
    with pytest.raises(OSError):
        private_fs.open_private(tmp_path / 'link', os.O_WRONLY | os.O_APPEND)
    (tmp_path / 'hard').unlink()
    target.chmod(0o640)
    with pytest.raises(PermissionError):
        private_fs.open_private(target, os.O_WRONLY | os.O_APPEND)
    os.close(private_fs.open_private(target, os.O_RDWR, tighten=True))      # a content-free lock file is tightened
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    monkeypatch.setattr(private_fs.os, 'getuid', lambda: os.geteuid() + 1)
    with pytest.raises(PermissionError):
        private_fs.read_private(target)
    assert target.read_bytes() == b'one\n'


def test_registry_store_refuses_an_unsafe_audit_log_for_reads_and_appends(tmp_path) -> None:
    store = FileRegistryStore(tmp_path / 'state' / 'capabilities')
    assert store.audit_events() == []
    store.append_audit({'event': 'one'})
    assert store.audit_events() == [{'event': 'one'}]
    assert stat.S_IMODE((tmp_path / 'state').stat().st_mode) == 0o700
    store.audit_path.chmod(0o666)
    for operation in (store.audit_events, lambda: store.append_audit({'event': 'two'})):
        with pytest.raises(Refusal) as refused:
            operation()
        assert (refused.value.status, refused.value.code, refused.value.reason) == (
            'UNAVAILABLE', 'TEMPORARILY_UNAVAILABLE', 'audit_unavailable')
        assert refused.value.__cause__ is None
    store.audit_path.chmod(0o600)
    assert store.audit_events() == [{'event': 'one'}]
    # A state directory that is a symlink is not tightened through the link; the root itself must be real.
    real = tmp_path / 'real'
    real.mkdir(mode=0o755)
    (tmp_path / 'alias').symlink_to(real, target_is_directory=True)
    FileRegistryStore(tmp_path / 'alias' / 'capabilities').append_audit({'event': 'x'})
    assert stat.S_IMODE(real.stat().st_mode) == 0o755
    assert stat.S_IMODE((real / 'capabilities').stat().st_mode) == 0o700


def test_refusals_and_exit_codes_follow_the_m01_table() -> None:
    code, value, diagnostic = rendering.failure(
        Refusal('UNAVAILABLE', 'TEMPORARILY_UNAVAILABLE', 'audit_unavailable', 'The audit log is not private.'))
    assert (code, value['status'], value['error']['code'], value['data'], diagnostic) == (
        5, 'UNAVAILABLE', 'TEMPORARILY_UNAVAILABLE', {'reason': 'audit_unavailable'}, None)
    expected = {'INTERNAL_ERROR': 1, 'INVALID_INPUT': 2, 'CONFIG_INVALID': 2, 'NOT_CONFIGURED': 3, 'UNSUPPORTED': 4,
                'UNAUTHENTICATED': 4, 'FORBIDDEN': 4, 'NOT_FOUND': 4, 'REVISION_CONFLICT': 4, 'BUDGET_EXCEEDED': 4,
                'TEMPORARILY_UNAVAILABLE': 5, 'DEADLINE_EXCEEDED': 5, 'OUTPUT_INVALID': 5}
    for name, exit_code in expected.items():
        assert rendering.exit_code({'status': 'BLOCKED', 'error': {'code': name}}) == exit_code, name
    assert rendering.exit_code({'status': 'SUCCEEDED', 'error': None}) == 0
    assert rendering.exit_code({'status': 'PARTIAL', 'error': None}) == 0
    assert rendering.exit_code({'status': 'DENIED', 'error': None}) == 4


def test_runtime_facts_are_measured_and_degrade_to_explicit_values(tmp_path, monkeypatch) -> None:
    assert [runtime_facts.os_qualification(name) for name in ('Linux', 'Darwin', 'Windows', 'SunOS')] == [
        'QUALIFIED', 'NOT_VERIFIED', 'NOT_VERIFIED', 'UNSUPPORTED']
    facts = runtime_facts.collect(tmp_path)
    assert facts['config_dir'] == str(tmp_path) and facts['sqlite_ok'] is facts['sqlite_fts5'] is True
    assert not any(tmp_path.iterdir())

    class NoFts:
        def execute(self, statement):
            raise sqlite3.OperationalError('no such module: fts5')

        def close(self):
            pass

    monkeypatch.setattr(runtime_facts.sqlite3, 'connect', lambda path: NoFts())
    assert runtime_facts.sqlite_fts5() is False and runtime_facts.collect(tmp_path)['sqlite_ok'] is False
    # Without /proc the descriptor table is scanned directly; closed descriptors are skipped.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)
        baseline = runtime_facts.listening_sockets()
        monkeypatch.setattr(runtime_facts.os, 'listdir', lambda path: (_ for _ in ()).throw(OSError(path)))
        assert runtime_facts.listening_sockets() == baseline == 1
        monkeypatch.setattr(runtime_facts.os, 'dup', lambda descriptor: (_ for _ in ()).throw(OSError(descriptor)))
        assert runtime_facts.listening_sockets() == 0          # a descriptor that cannot be inspected is not counted
        monkeypatch.undo()
        real_socket = socket.socket

        def refusing(*args, fileno=None, **kwargs):
            raise OSError('not a socket')

        monkeypatch.setattr(runtime_facts.socket, 'socket', refusing)
        assert runtime_facts.listening_sockets() == 0
        monkeypatch.undo()

        class Opaque(real_socket):
            def getsockopt(self, *args):
                raise OSError('option not supported')

        monkeypatch.setattr(runtime_facts.socket, 'socket', Opaque)
        assert runtime_facts.listening_sockets() == 0
        monkeypatch.undo()
    assert runtime_facts.listening_sockets() == 0


class StubIdentity:
    def __init__(self, authenticated=True):
        self.authenticated = authenticated
        self.calls = 0

    def diagnostics(self):
        return {'initialized': self.authenticated}

    def authenticate(self):
        self.calls += 1
        if not self.authenticated:
            raise AccessDenied()
        return type('Context', (), {'tenant_id': 'tenant-1'})()


class StubReports:
    """A feature-report store whose content is scripted per read (stale, replaced or malformed reports)."""

    def __init__(self, *loads):
        self.loads = list(loads)

    def load(self, config_hash):
        return self.loads.pop(0) if self.loads else None


def _stored(provider, clock, **changes):
    report = {'kind': 'feature_report', 'config_hash': provider.config_hash(), 'transport': provider.transport,
              'measured_at': clock().isoformat(), 'observed_model_id': 'fake-model-1',
              'model_identity_source': 'observed', 'aborted': None,
              'probe_profile': {'sha256': ask_probe_profile().sha256()},
              'features': {'tools': 'SUPPORTED', 'structured_output': 'SUPPORTED', 'streaming': 'weird'},
              'observations': {'tools': 'PROBE_PASSED', 'structured_output': 'PROBE_PASSED',
                               'streaming': 'STREAMING_UNSUPPORTED', 'timeout': 'NOT_RUN', 'concurrency': 'NOT_RUN'}}
    report.update(changes)
    return {'report': report, 'ref': 'sha256:' + 'ab' * 32 + ':/receipts/report.json'}


def test_doctor_measured_support_edges_with_scripted_stores(monkeypatch) -> None:
    """M17-RT-01 on doctor: only a current, unaltered report of this configuration counts as measured."""
    providers.transports()
    monkeypatch.setitem(providers._REGISTRY, FAKE_TRANSPORT, ScriptedFakeProvider)
    config = ProviderConfig(transport=FAKE_TRANSPORT, allow_live=True)
    provider = ScriptedFakeProvider(config, script=Script())
    clock = FakeClock()

    def doctor(*loads, identity=None, **facts):
        service = CLIService(identity or StubIdentity(), config, lambda record: {}, feature_reports=StubReports(*loads),
                             clock=clock, runtime_facts=(lambda: dict(facts)) if facts else None)
        return service.doctor()[1]['data']

    good = _stored(provider, clock)
    data = doctor(good, good)
    assert (data['provider']['status'], data['provider']['measured_support']) == ('PROBED', 'SUPPORTED')
    assert data['provider']['features']['streaming'] == 'NOT_VERIFIED'      # an unknown verdict is never trusted
    assert data['provider']['features']['timeout'] == 'NOT_VERIFIED'
    assert 'config_dir' not in data and data['behavior']['status'] == 'NOT_VERIFIED'
    # Replaced between the gate read and the report read; stale; aborted; malformed observations.
    assert doctor(good)['provider']['measured_support'] == 'NOT_VERIFIED'
    stale = _stored(provider, clock, measured_at='2020-01-01T00:00:00+00:00')
    assert doctor(stale, stale)['provider']['status'] == 'NOT_PROBED'
    aborted = _stored(provider, clock, aborted='UNAUTHENTICATED')
    data = doctor(aborted, aborted)['provider']
    assert (data['status'], data['measured_support']) == ('NOT_PROBED', 'SUPPORTED')
    malformed = _stored(provider, clock, observations=None)
    assert doctor(malformed, malformed)['provider']['status'] == 'NOT_PROBED'
    # One authentication per report, none when nothing needs it; an unauthenticated caller reads no report.
    identity = StubIdentity()
    doctor(good, good, identity=identity, config_dir='/profile', listening_sockets=0)
    assert identity.calls == 1
    anonymous = StubIdentity(authenticated=False)
    data = doctor(good, good, identity=anonymous, config_dir='/profile', os_qualification='NOT_VERIFIED',
                  sqlite_ok=False, listening_sockets=0)
    assert data['config_dir'] is None and data['provider']['measured_support'] == 'NOT_VERIFIED'
    assert {'os_not_qualified', 'sqlite_fts5_missing', 'identity_not_initialized'} <= set(data['warnings'])
    assert anonymous.calls == 1


def test_config_checks_classify_absent_and_invalid_configuration() -> None:
    def service(policy=None, behavior=None, config=None):
        return CLIService(StubIdentity(), config or ProviderConfig(transport='claude_cli', allow_live=True),
                          lambda record: {}, policy_loader=policy, behavior_check=behavior)

    state = type('State', (), {'available': False, 'cause': 'registry_wrong_mode'})()
    code, value = service(policy=lambda tenant_id: state).config_validate()
    checks = {item['name']: item for item in value['data']['checks']}
    assert (code, value['error']['code'], checks['policy']['status']) == (2, 'CONFIG_INVALID', 'INVALID')
    assert checks['behavior'] == {'name': 'behavior', 'status': 'NOT_CONFIGURED', 'reasons': ['behavior_not_verified']}
    assert value['data']['config_dir'] is None
    doctor = service(policy=lambda tenant_id: state).doctor()[1]['data']
    assert {'policy_unavailable:registry_wrong_mode', 'config_mode_too_open'} <= set(doctor['warnings'])
    assert doctor['config_valid'] is False
    code, value = service().config_validate('profile.toml')
    assert (code, value['error']['code']) == (4, 'UNSUPPORTED') and 'slice S03' in value['error']['message']
    with pytest.raises(KeyError):
        CLIService.unsupported('not-a-registered-command')


def test_behavior_use_cases_resolve_the_package_inside_the_root(tmp_path) -> None:
    tree = tmp_path / 'tree'
    for name in ('behavior', 'statecharts'):
        shutil.copytree(REPOSITORY_ROOT / 'examples' / name, tree / 'examples' / name)
    reference = 'examples/behavior/executive-secretary.yaml'
    assert behavior_commands.package_ref(reference, tree) == reference
    assert behavior_commands.package_ref(str(tree / reference), tree) == reference
    commands = behavior_commands.BehaviorCommands(StubIdentity())
    code, value = commands.validate(str(tree / reference), str(tree))
    assert (code, value['data']['package'], value['data']['ok']) == (0, reference, True)
    code, value = commands.render(str(tmp_path / 'outside.yaml'), str(tree))
    assert (code, value['error']['code'], value['data']['package']) == (2, 'CONFIG_INVALID', str(tmp_path / 'outside.yaml'))
    assert [item['reason'] for item in value['data']['diagnostics']] == ['PATH_TRAVERSAL']
    with pytest.raises(AccessDenied):
        behavior_commands.BehaviorCommands(StubIdentity(authenticated=False)).validate(reference, str(tree))
    status = behavior_commands.active_package_status(tree, 'examples/behavior/absent.yaml')
    assert (status['status'], status['diagnostics'][0]['reason'], status['rule_class']) == ('INVALID', 'REF_NOT_FOUND', 3)
