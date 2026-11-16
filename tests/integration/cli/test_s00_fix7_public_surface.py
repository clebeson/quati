"""S00 fix round 7: PUBLIC child-process proof of the storage, probe, identity and CLI-surface rules.

Findings of the independent re-audit (docs/audit/S00_FIX6_REAUDIT_2026-11-16.md, LOG-0041) covered
here: N1 (the data directory chain is verified before any read, lock, write or audit append; no
command commits a change and then reports failure), N7 (a probe authenticates, is authorized and
checks its storage before it spends a provider call), N10 (a present but rejected identity is
INVALID with its cause, never "not initialized", and never an INTERNAL_ERROR), N13/N16 (what
``tests/unit/test_s00_fix6_cli_surface.py`` proves in-process is proven here through real child
processes; the key canary also fails on a value that only the output redactor hides) and N15
(commands named by the specification exist and answer UNSUPPORTED; ``audit_unavailable`` uses the
M01 exit code of a local failure; a corrupted decision log refuses reads and writes alike).

Every test runs ``python -m quati ... --json`` (or the same public ``main`` through
``fixtures/fix7_public_runner.py`` when a scripted model or an observed foreign uid is needed) in a
fresh process with an isolated ``QUATI_CONFIG_DIR`` / ``QUATI_DATA_DIR``. Proof tier: L2
(deterministic, public entry). The model is a SCRIPTED FAKE: fake-provider compatibility only,
never evidence of a real provider. ``QUATI_ALLOW_LIVE=1`` is set only for child processes whose
transport is a scripted fake that cannot open a connection; the runner also refuses and records
every socket use.

Foreign ownership cannot be created without root or a second OS user. The foreign-owner tests use
the technique of the independent audit's ``runner4.py``: the child-process runner overrides the uid
that the process observes for one path (``os.stat``/``os.lstat``) or one inode (``os.fstat``). They
prove the refusal logic of the code, not a real multi-user host.
"""

from __future__ import annotations

import base64
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RUNNER = Path(__file__).resolve().parent / 'fixtures' / 'fix7_public_runner.py'
RESPONSE_KEYS = {'status', 'data', 'evidence_refs', 'uncertainties', 'next_action', 'error'}
FAKE, KEYED = 'scripted_fake_t04', 'scripted_fake_keyed'
SCRIPTED = {'QUATI_PROVIDER': FAKE, 'QUATI_ALLOW_LIVE': '1'}
CANARY = 'sk-quati-canary-5b8e2f90c7a14d63b1f0-NEVER-PRINT'
REDACTION_MARKER = '[REDACTED]'
WORK_TEXT = 'Find my next appointment'
READ_SCRIPT = [['classify'], ['search', 'next appointment calendar'], ['describe', 'fixtures.calendar-read'],
               ['invoke', 'fixtures.calendar-read', {'limit': 1}], ['final', 'done']]
INSTALL_MAIL = ('capabilities', 'install-fixture', 'mail-search', '--enable-fixture', '--json')
DISABLE_CALENDAR = ('capabilities', 'disable', 'fixtures.calendar-read@1.0.0', '--json')
LIST = ('capabilities', 'list', '--json')


class Run:
    def __init__(self, completed: subprocess.CompletedProcess, spy: list) -> None:
        self.code = completed.returncode
        self.out, self.err = completed.stdout.decode('utf-8'), completed.stderr.decode('utf-8')
        self.spy = spy

    @property
    def value(self) -> dict:
        lines = self.out.splitlines()
        assert len(lines) == 1, (self.out, self.err)      # M01-FR-01: exactly one Response object on stdout
        value = json.loads(lines[0])
        assert set(value) == RESPONSE_KEYS
        return value

    def kinds(self, kind: str) -> list:
        return [entry for entry in self.spy if entry[0] == kind]

    @property
    def summary(self) -> tuple:
        value = self.value
        return self.code, value['status'], (value['error'] or {}).get('code'), (value['data'] or {}).get('reason')


class Profile:
    """One isolated LOCAL profile driven only through child processes."""

    def __init__(self, root: Path) -> None:
        self.root, self.config, self.data = root, root / 'config', root / 'data'
        self.harness = root / 'harness'
        self.harness.mkdir()
        self.outputs: list[str] = []
        self.runs = 0

    def environment(self, extra: dict | None) -> dict:
        env = {name: value for name, value in os.environ.items()
               if not name.startswith('QUATI_') or name == 'QUATI_TEST_COVERAGE_BOOTSTRAP'}
        env['PYTHONPATH'] = os.pathsep.join(filter(None, [str(REPOSITORY_ROOT / 'src'),
                                                          os.environ.get('QUATI_TEST_COVERAGE_BOOTSTRAP')]))
        env.update(QUATI_CONFIG_DIR=str(self.config), QUATI_DATA_DIR=str(self.data), HOME=str(self.root / 'home'))
        env.update(extra or {})
        return env

    def run(self, *argv: str, env: dict | None = None, scenario: dict | None = None, stdin: bytes = b'') -> Run:
        self.runs += 1
        spy_log = self.harness / f'spy-{self.runs}.jsonl'
        if scenario is None:
            command = [sys.executable, '-m', 'quati', *argv]
        else:
            scenario_file = self.harness / f'scenario-{self.runs}.json'
            scenario_file.write_text(json.dumps(scenario), encoding='utf-8')
            command = [sys.executable, str(RUNNER), str(spy_log), str(scenario_file), *argv]
        completed = subprocess.run(command, cwd=self.harness, env=self.environment(env), input=stdin,
                                   capture_output=True, check=False, timeout=120)
        spy = [json.loads(line) for line in spy_log.read_text(encoding='utf-8').splitlines()] if spy_log.exists() else []
        result = Run(completed, spy)
        self.outputs += [result.out, result.err]
        return result

    def scripted(self, *argv: str, script: list | None = None, env: dict | None = None, **scenario) -> Run:
        return self.run(*argv, env={**SCRIPTED, **(env or {})}, scenario={'script': script or [], **scenario})

    def ready(self) -> None:
        """Initialized profile, calendar-read enabled and a successful scripted probe."""
        assert self.run('init', '--json').code == 0
        assert self.run('capabilities', 'install-fixture', 'calendar-read', '--enable-fixture', '--json').code == 0
        probe = self.scripted('models', 'probe', '--json')
        assert (probe.code, probe.value['status']) == (0, 'SUCCEEDED'), probe.out

    def files(self) -> dict:
        return {str(path.relative_to(self.root)): path.read_bytes()
                for base in (self.config, self.data) if base.exists() and not base.is_symlink()
                for path in sorted(base.rglob('*')) if path.is_file() and not path.is_symlink()}

    def tree(self, base: Path) -> dict:
        return {str(path.relative_to(base)): (path.read_bytes() if path.is_file() else None)
                for path in sorted(base.rglob('*')) if not path.is_symlink()}

    def audit(self) -> list:
        log = self.data / 'capabilities' / 'audit.jsonl'
        return [json.loads(line) for line in log.read_text(encoding='utf-8').splitlines()] if log.exists() else []

    def lifecycles(self) -> dict:
        listed = self.run(*LIST)
        assert listed.code == 0, listed.out
        return {item['capability_id']: item['lifecycle'] for item in listed.value['data']['capabilities']}

    def resign(self, **changes) -> None:
        """Rewrite the installation record with ``changes`` (None removes a field), signed by the device key."""
        record = json.loads((self.config / 'identity.json').read_bytes())
        record.pop('signature')
        for name, value in changes.items():
            if value is None:
                record.pop(name, None)
            else:
                record[name] = value
        key = Ed25519PrivateKey.from_private_bytes((self.config / 'device.key').read_bytes())
        canonical = json.dumps(record, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8')
        record['signature'] = base64.b64encode(key.sign(canonical)).decode('ascii')
        (self.config / 'identity.json').write_bytes(
            json.dumps(record, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8'))


@pytest.fixture
def profile(tmp_path) -> Profile:
    return Profile(tmp_path)


def assert_unsafe_state(run: Run, component: str) -> None:
    """The typed refusal of an unusable data directory chain: M01 exit 4 (local, not a provider failure)."""
    value = run.value
    assert run.summary == (4, 'UNAVAILABLE', 'TEMPORARILY_UNAVAILABLE', 'state_dir_unsafe'), run.out
    assert value['data'] == {'reason': 'state_dir_unsafe', 'component': component}
    assert value['evidence_refs'] == [] and 'internal error' not in run.err


# ----------------------------------------------------------------- N13: probes authenticate first (public)
@pytest.mark.parametrize('argv', [('models', 'probe', '--json'), ('doctor', '--probe', '--json')])
def test_n13_probe_without_identity_is_denied_before_any_provider_call_or_write(profile: Profile, argv) -> None:
    """IDN-01 / M02 order row 1 on the public path: UNAUTHENTICATED, zero provider calls, nothing created."""
    run = profile.scripted(*argv)
    assert run.summary == (4, 'DENIED', 'UNAUTHENTICATED', None) and run.value['data'] is None
    assert run.kinds('probe_call') == [] and run.kinds('socket') == []
    assert not profile.data.exists() and not profile.config.exists()
    assert profile.run('init', '--json').code == 0
    before = profile.files()
    run = profile.scripted(*argv, env={'QUATI_CAPABILITY_CONTEXT': '1'})
    assert run.summary == (4, 'DENIED', 'UNAUTHENTICATED', None)
    assert run.kinds('probe_call') == [] and profile.files() == before


# ----------------------------------------------------------------- N7: authorization and storage before the call
@pytest.mark.parametrize('argv', [('models', 'probe', '--json'), ('doctor', '--probe', '--json')])
def test_n7_an_authorized_probe_logs_its_decision_before_the_provider_call(profile: Profile, argv) -> None:
    """M02 order rows 4 and 7: ``manage`` on the tenant registry, logged as ``authz.decided``, then one probe."""
    assert profile.run('init', '--json').code == 0
    run = profile.scripted(*argv)
    assert (run.code, run.value['status']) == (0, 'SUCCEEDED'), run.out
    assert len(run.kinds('probe_call')) == 1
    decisions = [event for event in profile.audit() if event['event'] == 'authz.decided']
    assert [(event['operation'], event['decision']['action'], event['decision']['verdict'],
             event['decision']['reason_code']) for event in decisions] == [('models_probe', 'manage', 'ALLOW', 'OK')]
    assert decisions[0]['decision']['resource_ref'] == f"registry:{decisions[0]['tenant_id']}"
    names = set(profile.files())
    assert any(name.startswith('data/feature_reports/') for name in names)
    assert any(name.startswith('data/receipts/') for name in names)


@pytest.mark.parametrize(('role', 'reason'), [('MEMBER', 'ROLE_INSUFFICIENT'), ('GUEST', 'NO_SPACE_GRANT'),
                                               ('guest', 'NO_SPACE_GRANT')])
@pytest.mark.parametrize('argv', [('models', 'probe', '--json'), ('doctor', '--probe', '--json')])
def test_n7_a_principal_that_may_not_manage_the_registry_cannot_probe(profile: Profile, argv, role, reason) -> None:
    """A probe replaces the report that gates ``ask``: without the tenant role it is denied before the call."""
    assert profile.run('init', '--json').code == 0
    profile.resign(tenant_role=role)
    before = {name for name in profile.files() if not name.endswith('audit.jsonl')}
    run = profile.scripted(*argv)
    assert run.summary == (4, 'DENIED', 'FORBIDDEN', reason), run.out
    assert run.kinds('probe_call') == [] and run.value['evidence_refs'] == []
    assert {name for name in profile.files() if not name.endswith('audit.jsonl')} == before
    decision = [event for event in profile.audit() if event['event'] == 'authz.decided'][-1]
    assert (decision['operation'], decision['decision']['verdict'], decision['decision']['reason_code']) == (
        'models_probe', 'DENY', reason)


@pytest.mark.parametrize('fault', ['data_symlink', 'receipts_symlink', 'feature_reports_symlink', 'data_foreign_path',
                                   'receipts_foreign_inode', 'feature_reports_file'])
@pytest.mark.parametrize('argv', [('models', 'probe', '--json'), ('doctor', '--probe', '--json')])
def test_n7_a_probe_refuses_unusable_storage_before_spending_the_call(profile: Profile, argv, fault) -> None:
    """No probe spends a provider call and then fails to store its result; no symlink is followed."""
    assert profile.run('init', '--json').code == 0
    assert profile.scripted('models', 'probe', '--json').code == 0     # receipts/ and feature_reports/ now exist
    name, kind = fault.rsplit('_', 2)[0] if fault.endswith(('_path', '_inode')) else fault.rsplit('_', 1)[0], fault
    target = profile.data if name == 'data' else profile.data / name
    component, scenario, guarded = ('data_dir' if name == 'data' else name), {}, profile.data
    if kind.endswith('_symlink'):
        guarded = profile.root / 'victim'
        target.rename(guarded)
        target.symlink_to(guarded, target_is_directory=True)
    elif kind.endswith('_foreign_path'):
        scenario = {'foreign_paths': [str(target)]}
    elif kind.endswith('_foreign_inode'):
        scenario = {'foreign_inodes': [str(target)]}
    else:
        for path in target.iterdir():
            path.unlink()
        target.rmdir()
        target.write_bytes(b'not a directory')
    victim = guarded
    before = profile.tree(victim)
    run = profile.scripted(*argv, **scenario)
    assert_unsafe_state(run, component)
    assert run.kinds('probe_call') == [] and profile.tree(victim) == before


# ----------------------------------------------------------------- N1: the data directory chain fails closed
COMMANDS = {'list': (LIST, None), 'install': (INSTALL_MAIL, None), 'disable': (DISABLE_CALENDAR, None),
            'greeting': (('ask', 'hello', '--json'), None), 'ask': (('ask', WORK_TEXT, '--json'), READ_SCRIPT)}


def _command(profile: Profile, name: str, **scenario) -> Run:
    argv, script = COMMANDS[name]
    return profile.scripted(*argv, script=script, **scenario)


@pytest.mark.parametrize('name', list(COMMANDS))
def test_n1_a_symlinked_data_directory_is_refused_before_any_read_or_write(profile: Profile, name: str) -> None:
    """A data directory that is a symlink: typed refusal, nothing read, written or executed below the target."""
    profile.ready()
    real = profile.root / 'real-data'
    profile.data.rename(real)
    profile.data.symlink_to(real, target_is_directory=True)
    before = profile.tree(real)
    run = _command(profile, name)
    assert_unsafe_state(run, 'data_dir')
    assert run.kinds('handler') == [] and run.kinds('request') == [] and profile.tree(real) == before


@pytest.mark.parametrize('simulation', ['foreign_paths', 'foreign_inodes'])
@pytest.mark.parametrize('name', list(COMMANDS))
def test_n1_a_data_directory_of_another_user_is_refused_and_nothing_is_committed(
        profile: Profile, name: str, simulation: str) -> None:
    """Simulated foreign owner (see the module docstring): no registry change, no audit line, no handler."""
    profile.ready()
    before = profile.tree(profile.data)
    run = _command(profile, name, **{simulation: [str(profile.data)]})
    assert_unsafe_state(run, 'data_dir')
    assert run.kinds('handler') == [] and run.kinds('request') == [] and profile.tree(profile.data) == before
    assert profile.lifecycles() == {'fixtures.calendar-read': 'ENABLED'}


@pytest.mark.parametrize(('name', 'component'), [
    ('install', 'capabilities'), ('install', 'receipts'), ('install', 'fixture_sources'),
    ('disable', 'capabilities'), ('disable', 'receipts')])
def test_n1_no_registry_change_is_committed_when_a_directory_it_needs_is_unusable(
        profile: Profile, name: str, component: str) -> None:
    """Durability order: the receipt and source directories are verified before the registry is touched."""
    profile.ready()
    target, moved = profile.data / component, profile.root / 'moved'
    target.rename(moved)
    target.symlink_to(moved, target_is_directory=True)
    before = profile.tree(profile.data), profile.tree(moved)
    run = _command(profile, name)
    assert_unsafe_state(run, component)
    assert (profile.tree(profile.data), profile.tree(moved)) == before
    target.unlink()
    moved.rename(target)
    assert profile.lifecycles() == {'fixtures.calendar-read': 'ENABLED'}


def test_n1_init_refuses_an_unusable_data_directory_before_creating_an_identity(profile: Profile) -> None:
    """``quati init`` writes a receipt: an unusable data directory refuses it before any credential exists."""
    real = profile.root / 'real-data'
    real.mkdir()
    profile.data.symlink_to(real, target_is_directory=True)
    run = profile.run('init', '--json')
    assert_unsafe_state(run, 'data_dir')
    assert list(real.iterdir()) == [] and not (profile.config / 'identity.json').exists()
    profile.data.unlink()
    assert profile.run('init', '--json').code == 0


def _modes(profile: Profile) -> list:
    return [(str(path.relative_to(profile.root)), oct(stat.S_IMODE(path.lstat().st_mode)))
            for path in [profile.data, *sorted(profile.data.rglob('*'))]
            if stat.S_IMODE(path.lstat().st_mode) != (0o700 if path.is_dir() else 0o600)]


def test_n13_the_registry_store_alone_makes_a_permissive_data_directory_private(profile: Profile) -> None:
    """Store leg (no receipt is written by ``capabilities list``): ``data/`` created 0777 becomes 0700."""
    assert profile.run('init', '--json').code == 0
    for path in profile.data.rglob('*'):
        path.unlink() if path.is_file() else None
    for path in sorted(profile.data.rglob('*'), reverse=True):
        path.rmdir()
    profile.data.chmod(0o777)
    run = profile.run(*LIST, scenario={'umask': 0})
    assert run.code == 0, run.out
    assert not (profile.data / 'receipts').exists() and (profile.data / 'capabilities' / 'audit.jsonl').exists()
    assert _modes(profile) == []


def test_n13_the_receipt_writer_alone_makes_a_permissive_data_directory_private(profile: Profile) -> None:
    """Receipt leg (a greeting touches no registry file): ``data/`` created 0777 becomes 0700."""
    assert profile.run('init', '--json').code == 0
    for path in profile.data.rglob('*'):
        path.unlink() if path.is_file() else None
    for path in sorted(profile.data.rglob('*'), reverse=True):
        path.rmdir()
    profile.data.chmod(0o777)
    run = profile.run('ask', 'hello', '--json', scenario={'umask': 0})
    assert run.code == 0, run.out
    assert not (profile.data / 'capabilities').exists() and list((profile.data / 'receipts').iterdir())
    assert _modes(profile) == []


def test_n13_everything_quati_creates_under_a_zero_umask_is_owner_only(profile: Profile) -> None:
    """Under umask 000 every directory is 0700 and every file 0600, the fixture source tree included
    (``fixture_capabilities.write_fixture_package`` makes the tree it writes private; integration item B1)."""
    zero = {'umask': 0}
    assert profile.run('init', '--json', scenario=zero).code == 0
    assert profile.run('capabilities', 'install-fixture', 'calendar-read', '--enable-fixture', '--json',
                       scenario=zero).code == 0
    assert profile.scripted('models', 'probe', '--json', **zero).code == 0
    run = profile.scripted('ask', WORK_TEXT, '--json', script=READ_SCRIPT, **zero)
    assert run.code == 0 and run.kinds('handler') == [['handler', 'calendar-read']], run.out
    assert stat.S_IMODE((profile.data / 'fixture_sources').stat().st_mode) == 0o700
    assert any(path.is_file() for path in (profile.data / 'fixture_sources').rglob('*'))
    assert _modes(profile) == []


# ----------------------------------------------------------------- N13 / N15: the audit log on the public path
def _log(profile: Profile) -> Path:
    return profile.data / 'capabilities' / 'audit.jsonl'


def _audit_fault(profile: Profile, fault: str) -> dict:
    """Make the audit log unsafe; return the runner scenario that goes with the fault."""
    log = _log(profile)
    if fault == 'hard_link':
        os.link(log, profile.root / 'second-name')
    elif fault == 'foreign_owner':
        return {'foreign_inodes': [str(log)]}
    elif fault == 'directory':
        log.unlink()
        log.mkdir()
    elif fault == 'corrupt_line':
        log.write_bytes(log.read_bytes() + b'{"event": "torn\n')
    elif fault == 'not_an_object':
        log.write_bytes(log.read_bytes() + b'["an", "array"]\n')
    else:
        log.chmod(int(fault.removeprefix('mode_'), 8))
    return {}


@pytest.mark.parametrize('fault', ['hard_link', 'foreign_owner', 'directory', 'mode_644', 'mode_640', 'mode_604',
                                   'mode_000', 'corrupt_line', 'not_an_object'])
@pytest.mark.parametrize('name', ['list', 'install', 'ask'])
def test_n13_an_unsafe_or_unreadable_audit_log_refuses_reads_and_writes_alike(
        profile: Profile, name: str, fault: str) -> None:
    """K7 / M26 / M02 decision log: every registry command and a read ask fail closed with exit 4."""
    profile.ready()
    scenario = _audit_fault(profile, fault)
    log = _log(profile)
    before = log.read_bytes() if log.is_file() and stat.S_IMODE(log.stat().st_mode) & 0o400 else None
    registry = (profile.data / 'capabilities' / 'registry.json').read_bytes()
    run = _command(profile, name, **scenario)
    assert run.summary == (4, 'UNAVAILABLE', 'TEMPORARILY_UNAVAILABLE', 'audit_unavailable'), run.out
    assert run.kinds('handler') == [] and 'internal error' not in run.err
    assert (profile.data / 'capabilities' / 'registry.json').read_bytes() == registry
    if before is not None:
        assert log.read_bytes() == before


@pytest.mark.parametrize('name', ['list', 'install', 'ask'])
def test_n13_an_audit_log_that_is_a_fifo_with_a_reader_receives_nothing(profile: Profile, name: str) -> None:
    """The regular-file check: a FIFO that somebody reads would accept the append; it is refused instead."""
    profile.ready()
    log = _log(profile)
    log.unlink()
    os.mkfifo(log, 0o600)
    reader = os.open(log, os.O_RDONLY | os.O_NONBLOCK)
    try:
        run = _command(profile, name)
        assert run.summary == (4, 'UNAVAILABLE', 'TEMPORARILY_UNAVAILABLE', 'audit_unavailable'), run.out
        assert run.kinds('handler') == []
        try:
            leaked = os.read(reader, 65536)
        except BlockingIOError:
            leaked = b''
        assert leaked == b''
    finally:
        os.close(reader)


# ----------------------------------------------------------------- N10: a present but rejected identity
def _break_identity(profile: Profile, fault: str) -> dict:
    record, key = profile.config / 'identity.json', profile.config / 'device.key'
    if fault == 'record_mode':
        record.chmod(0o644)
    elif fault == 'key_mode':
        key.chmod(0o640)
    elif fault == 'directory_mode':
        profile.config.chmod(0o755)
    elif fault == 'record_symlink':
        copy = profile.root / 'identity-copy.json'
        copy.write_bytes(record.read_bytes())
        copy.chmod(0o600)
        record.unlink()
        record.symlink_to(copy)
    elif fault == 'directory_symlink':
        moved = profile.root / 'config-real'
        profile.config.rename(moved)
        profile.config.symlink_to(moved, target_is_directory=True)
    elif fault == 'record_corrupt':
        record.write_bytes(b'{"schema_version": "quati-local-identity/1", ')
    elif fault == 'record_not_an_object':
        record.write_bytes(b'[1, 2, 3]')
    elif fault == 'bad_signature':
        value = json.loads(record.read_bytes())
        value['tenant_role'] = 'OWNER'
        record.write_bytes(json.dumps(value).encode('utf-8'))
    elif fault == 'field_missing':
        profile.resign(organization_space_id=None)
    elif fault == 'field_wrong_type':
        profile.resign(personal_space_id=7)
    elif fault == 'key_missing':
        key.unlink()
    elif fault == 'record_missing':
        record.unlink()
    elif fault == 'record_foreign_owner':
        return {'foreign_paths': [str(record)], 'foreign_inodes': [str(record)]}
    return {}


IDENTITY_FAULTS = {
    'record_mode': ('credential_insecure', 'identity_file_mode'),
    'key_mode': ('credential_insecure', 'device_key_mode'),
    'directory_mode': ('credential_insecure', 'config_dir_mode'),
    'record_symlink': ('credential_insecure', 'identity_file_symlink'),
    'directory_symlink': ('credential_insecure', 'config_dir_symlink'),
    'record_foreign_owner': ('credential_insecure', 'identity_file_owner'),
    'record_corrupt': ('credential_corrupt', 'record_not_json'),
    'record_not_an_object': ('credential_corrupt', 'record_not_json'),
    'bad_signature': ('credential_corrupt', 'record_rejected'),
    'field_missing': ('credential_corrupt', 'record_field_missing'),
    'field_wrong_type': ('credential_corrupt', 'record_field_missing'),
    'key_missing': ('credential_corrupt', 'device_key_missing'),
    'record_missing': ('credential_corrupt', 'identity_file_missing'),
}


@pytest.mark.parametrize('fault', list(IDENTITY_FAULTS))
def test_n10_a_rejected_identity_is_reported_invalid_with_its_cause(profile: Profile, fault: str) -> None:
    """M01 ``ConfigValidation`` (INVALID = present but rejected) and the M02 reason table, on the public path."""
    assert profile.run('init', '--json').code == 0
    scenario = _break_identity(profile, fault)
    cause, detail = IDENTITY_FAULTS[fault]
    before = profile.files()
    doctor = profile.run('doctor', '--json', scenario=scenario)
    data = doctor.value['data']
    assert (doctor.code, doctor.value['status']) == (0, 'SUCCEEDED'), doctor.out
    assert (data['identity']['initialized'], data['identity']['status'], data['identity']['reason'],
            data['identity']['detail']) == (False, 'INVALID', cause, detail)
    assert f'identity_invalid:{cause}' in data['warnings'] and 'identity_not_initialized' not in data['warnings']
    assert ('config_mode_too_open' in data['warnings']) == detail.endswith('_mode')
    assert data['config_valid'] is False and data['config_dir'] is None
    assert '`quati doctor`' in doctor.value['next_action'] and 'quati init' not in doctor.value['next_action']
    validate = profile.run('config', 'validate', '--json', scenario=scenario)
    checks = {item['name']: item for item in validate.value['data']['checks']}
    assert validate.summary[:3] == (2, 'DENIED', 'CONFIG_INVALID') and validate.value['data']['valid'] is False
    assert checks['identity'] == {'name': 'identity', 'status': 'INVALID', 'reasons': [cause, detail]}
    assert f'identity: INVALID ({cause}, {detail})' in validate.value['uncertainties']
    assert 'quati init' not in validate.value['next_action'] and '`quati doctor`' in validate.value['next_action']
    # No command turns a rejected credential into an internal error: each is the typed identity denial.
    for argv in (('ask', 'hello', '--json'), LIST, ('models', 'probe', '--json'), ('doctor', '--probe', '--json')):
        denied = profile.scripted(*argv, **scenario)
        assert denied.summary == (4, 'DENIED', 'UNAUTHENTICATED', None), (argv, denied.out, denied.err)
        assert denied.kinds('probe_call') == [] and 'internal error' not in denied.err
    assert profile.files() == before
    assert str(profile.config) not in ''.join(profile.outputs)      # no profile path for an unauthenticated caller


@pytest.mark.parametrize('prepared', ['nothing', 'empty_directory'])
def test_n10_an_absent_identity_stays_not_configured_with_the_init_route(profile: Profile, prepared: str) -> None:
    """Control: only a credential that does not exist is ``credential_missing`` -> ``quati init``."""
    if prepared == 'empty_directory':
        profile.config.mkdir(mode=0o700)
    doctor = profile.run('doctor', '--json')
    data = doctor.value['data']
    assert (doctor.code, data['identity']['status'], data['identity']['reason']) == (
        0, 'NOT_CONFIGURED', 'credential_missing')
    assert 'identity_not_initialized' in data['warnings']
    assert not [tag for tag in data['warnings'] if tag.startswith('identity_invalid')]
    validate = profile.run('config', 'validate', '--json')
    checks = {item['name']: item for item in validate.value['data']['checks']}
    assert (validate.code, validate.value['status'], validate.value['data']['valid']) == (0, 'PARTIAL', True)
    assert checks['identity'] == {'name': 'identity', 'status': 'NOT_CONFIGURED', 'reasons': ['identity_not_initialized']}
    assert 'quati init' in validate.value['next_action']


# ----------------------------------------------------------------- N13: config validate and the doctor report
def test_n13_config_validate_reports_each_check_through_the_public_entry(profile: Profile) -> None:
    run = profile.run('config', 'validate', '--json')
    checks = {item['name']: item for item in run.value['data']['checks']}
    assert (run.code, run.value['status'], run.value['data']['valid']) == (0, 'PARTIAL', True)
    assert list(checks) == ['identity', 'policy', 'provider', 'behavior']
    assert [checks[name]['status'] for name in checks] == ['NOT_CONFIGURED', 'NOT_CONFIGURED', 'NOT_CONFIGURED', 'OK']
    assert checks['provider']['reasons'][:2] == ['API_KEY_MISSING', 'LIVE_NOT_ALLOWED']
    assert run.value['data']['config_dir'] is None and profile.files() == {}
    assert profile.run('init', '--json').code == 0
    files = profile.files()
    run = profile.scripted('config', 'validate', '--json')
    assert (run.code, run.value['status'], run.value['data']['valid'], run.value['uncertainties']) == (
        0, 'SUCCEEDED', True, [])
    assert {item['status'] for item in run.value['data']['checks']} == {'OK'}
    assert run.value['data']['config_dir'] == str(profile.config) and profile.files() == files
    (profile.config / 'policy.json').chmod(0o644)
    run = profile.scripted('config', 'validate', '--json')
    checks = {item['name']: item for item in run.value['data']['checks']}
    assert run.summary[:3] == (2, 'DENIED', 'CONFIG_INVALID')
    assert checks['policy'] == {'name': 'policy', 'status': 'INVALID', 'reasons': ['wrong_mode']}
    (profile.config / 'policy.json').chmod(0o600)
    run = profile.run('config', 'validate', '--json', env={'QUATI_PROVIDER': 'no-such-transport'})
    checks = {item['name']: item for item in run.value['data']['checks']}
    assert run.summary[:3] == (2, 'DENIED', 'CONFIG_INVALID')
    assert checks['provider'] == {'name': 'provider', 'status': 'INVALID', 'reasons': ['TRANSPORT_UNKNOWN']}
    assert profile.files() == files


DOCTOR_FIELDS = {'profile', 'os', 'os_qualification', 'python_version', 'sqlite_version', 'sqlite_fts5',
                 'sqlite_journal_mode', 'sqlite_journal_reason', 'sqlite_ok', 'config_dir', 'config_valid', 'provider',
                 'live_calls_allowed', 'listening_sockets', 'worker', 'policy', 'behavior', 'warnings'}


def test_n13_the_doctor_report_is_measured_through_the_public_entry(profile: Profile) -> None:
    """M01 ``DoctorReport`` before init, after init and after a scripted probe, each in its own process."""
    fresh = profile.run('doctor', '--json')
    data = fresh.value['data']
    assert fresh.code == 0 and DOCTOR_FIELDS <= set(data)
    assert (data['profile'], data['config_dir'], data['live_calls_allowed'], data['listening_sockets']) == (
        'LOCAL', None, False, 0)
    assert (data['provider']['status'], data['provider']['measured_support']) == ('NOT_CONFIGURED', 'NOT_VERIFIED')
    assert data['policy'] == {'status': 'UNAVAILABLE', 'reason': 'missing'} and profile.files() == {}
    assert profile.run('init', '--json').code == 0
    files = profile.files()
    data = profile.scripted('doctor', '--json').value['data']
    assert DOCTOR_FIELDS <= set(data) and data['config_dir'] == str(profile.config)
    assert (data['provider']['status'], data['provider']['measured_support'], data['live_calls_allowed']) == (
        'NOT_PROBED', 'NOT_VERIFIED', True)
    assert data['identity']['status'] == 'AVAILABLE' and data['policy']['status'] == 'AVAILABLE'
    assert profile.files() == files                              # plain doctor is read-only
    probe = profile.scripted('models', 'probe', '--json')
    assert probe.code == 0
    files = profile.files()
    after = profile.scripted('doctor', '--json')
    provider = after.value['data']['provider']
    assert (provider['status'], provider['measured_support']) == ('PROBED', 'SUPPORTED')
    assert provider['features'] == probe.value['data']['feature_report']['features']
    assert provider['feature_report']['ref'] == probe.value['evidence_refs'][0]
    assert after.kinds('probe_call') == [] and profile.files() == files
    # A stored measurement is read only from a private store: a symlinked directory is not followed.
    moved = profile.root / 'reports'
    (profile.data / 'feature_reports').rename(moved)
    (profile.data / 'feature_reports').symlink_to(moved, target_is_directory=True)
    provider = profile.scripted('doctor', '--json').value['data']['provider']
    assert (provider['status'], provider['measured_support']) == ('NOT_PROBED', 'NOT_VERIFIED')


def test_n13_m01_at_01_negative_with_the_real_live_allowance_variable(profile: Profile) -> None:
    """M01-AT-01 negative: ``QUATI_ALLOW_LIVE=1`` set for real, key missing -> NOT_CONFIGURED, no network use.

    The transport is the scripted fake declared as an API-key transport; it cannot open a connection,
    and the runner refuses and records any socket use.
    """
    env = {'QUATI_PROVIDER': KEYED, 'QUATI_ALLOW_LIVE': '1'}
    run = profile.run('doctor', '--json', env=env, scenario={})
    data = run.value['data']
    assert run.code == 0 and (data['provider']['status'], data['live_calls_allowed'], data['listening_sockets']) == (
        'NOT_CONFIGURED', True, 0)
    assert data['provider']['reasons'] == ['API_KEY_MISSING']
    assert run.kinds('socket') == [] and run.kinds('probe_call') == [] and profile.files() == {}
    assert profile.run('init', '--json').code == 0
    for argv in (('models', 'probe', '--json'), ('doctor', '--probe', '--json'), ('ask', WORK_TEXT, '--json')):
        run = profile.run(*argv, env=env, scenario={})
        assert run.summary[:3] == (3, 'BLOCKED', 'NOT_CONFIGURED'), run.out
        assert run.kinds('socket') == [] and run.kinds('probe_call') == [] and run.kinds('request') == []
    # The variable itself is what opens the live path: without it the same configuration is refused,
    # with it and a key the scripted probe runs (still without any socket).
    key = {'QUATI_API_KEY': 'sk-synthetic-0123456789abcdef'}
    run = profile.run('models', 'probe', '--json', env={'QUATI_PROVIDER': KEYED, **key}, scenario={})
    assert run.summary[:3] == (3, 'BLOCKED', 'NOT_CONFIGURED') and run.kinds('probe_call') == []
    assert run.value['data']['provider']['reasons'] == ['LIVE_NOT_ALLOWED']
    assert profile.run('doctor', '--json', env={'QUATI_PROVIDER': KEYED, **key},
                       scenario={}).value['data']['live_calls_allowed'] is False
    run = profile.run('models', 'probe', '--json', env={**env, **key}, scenario={})
    assert (run.code, run.value['status']) == (0, 'SUCCEEDED') and len(run.kinds('probe_call')) == 1
    assert run.kinds('socket') == []


# ----------------------------------------------------------------- N16: the key canary on every public output
def _scan(profile: Profile, *needles: str) -> list:
    found = [f'output {index}: {needle}' for index, text in enumerate(profile.outputs)
             for needle in needles if needle in text]
    for base in (profile.config, profile.data):
        for path in sorted(base.rglob('*')):
            if path.is_file() and not path.is_symlink():
                blob = path.read_bytes()
                found += [f'{path.relative_to(profile.root)}: {needle}' for needle in needles
                          if needle.encode('utf-8') in blob]
    return found


def _trace(profile: Profile, request_id: str, env: dict) -> None:
    show = profile.run('trace', 'show', request_id, '--json', env=env)
    assert show.code == 0, show.out
    profile.run('trace', 'explain', request_id, '--json', env=env)
    profile.run('trace', 'show', request_id, env=env)


def test_n16_a_configured_key_never_reaches_any_output_even_behind_the_redactor(profile: Profile) -> None:
    """GATE-01 canary: the key is absent from stdout, stderr, receipts, reports, the audit log and traces.

    Here the environment is the only source of the key (no requester or model repeats it), so the
    output redactor must have nothing to hide: its marker in any output means that a use case put
    the key into a Response or a stored record (the auditor's mutant: the key appended to the
    LIVE_NOT_ALLOWED hint). The vendor transport is never allowed live in this test.
    """
    env = {'QUATI_API_KEY_ENV': 'QUATI_CANARY_KEY', 'QUATI_CANARY_KEY': CANARY, 'QUATI_PROVIDER': 'openai_compatible',
           'QUATI_BASE_URL': 'https://models.invalid/v1', 'QUATI_MODEL': 'synthetic-model'}
    assert profile.run('init', '--json', env=env).code == 0
    doctor = profile.run('doctor', '--json', env=env, scenario={})
    reasons = doctor.value['data']['provider']['reasons']
    assert doctor.code == 0 and reasons[0] == 'LIVE_NOT_ALLOWED'                      # the key itself was accepted
    assert not {'API_KEY_MISSING', 'API_KEY_REF_INVALID'} & set(reasons)
    assert profile.run('doctor', env=env).code == 0                                   # human rendering
    for argv in (('doctor', '--probe', '--json'), ('models', 'probe', '--json'), ('ask', WORK_TEXT, '--json')):
        run = profile.run(*argv, env=env, scenario={})
        assert run.code == 3 and run.kinds('socket') == [], run.out
    request_id = run.value['data']['request_id']
    assert profile.run('ask', 'hello', '--json', env=env).code == 0
    assert profile.run('config', 'validate', '--json', env=env).code == 0
    assert profile.run(*LIST, env=env).code == 0
    chat = profile.run('chat', '--jsonl', env=env, stdin=f'Hello\n{WORK_TEXT}\n/help\n/quit\n'.encode())
    assert chat.code == 0 and len(chat.out.splitlines()) == 4
    _trace(profile, request_id, env)
    assert any(name.startswith('data/receipts/') for name in profile.files())
    assert _scan(profile, CANARY, REDACTION_MARKER) == []


def test_n16_a_key_repeated_by_the_requester_and_the_model_is_stored_and_shown_nowhere(profile: Profile) -> None:
    """A scripted model and a requester that both repeat the key cannot get its value into any output or file."""
    env = {'QUATI_PROVIDER': KEYED, 'QUATI_ALLOW_LIVE': '1', 'QUATI_API_KEY_ENV': 'QUATI_CANARY_KEY',
           'QUATI_CANARY_KEY': CANARY}
    assert profile.run('init', '--json', env=env).code == 0
    assert profile.run('capabilities', 'install-fixture', 'calendar-read', '--enable-fixture', '--json', env=env).code == 0
    assert profile.run('models', 'probe', '--json', env=env, scenario={}).code == 0
    assert profile.run('doctor', '--probe', '--json', env=env, scenario={}).code == 0
    assert profile.run('doctor', '--json', env=env, scenario={}).value['data']['provider']['status'] == 'PROBED'
    script = [['classify'], ['search', f'next appointment calendar {CANARY}'], ['describe', 'fixtures.calendar-read'],
              ['invoke', 'fixtures.calendar-read', {'limit': 1}], ['final', f'The key is {CANARY}']]
    ask = profile.run('ask', f'{WORK_TEXT} {CANARY}', '--json', '--synthetic-evidence', env=env,
                      scenario={'script': script})
    assert ask.code == 0 and ask.kinds('handler') == [['handler', 'calendar-read']], ask.out
    chat = profile.run('chat', '--jsonl', env=env, scenario={'script': script},
                       stdin=f'{WORK_TEXT} {CANARY}\n/quit\n'.encode())
    assert chat.code == 0 and len(chat.out.splitlines()) == 2
    _trace(profile, ask.value['data']['request_id'], env)
    names = set(profile.files())
    assert 'data/capabilities/audit.jsonl' in names
    assert any(name.startswith('data/receipts/') for name in names)
    assert any(name.startswith('data/feature_reports/') for name in names)
    assert _scan(profile, CANARY) == []


# ----------------------------------------------------------------- N15: commands named by the specification
SPECIFIED_LATER = [
    (('server',), 'S05'), (('server', '--port', '8080'), 'S05'), (('login',), 'S05'),
    (('grants', 'list', 'space-1'), 'S05'),
    (('spaces', 'describe', 'space-1'), 'S02'), (('policy', 'apply', 'policy.json'), 'S02'),
    (('policy', 'apply', 'policy.json', '--adopt'), 'S02'), (('policy', 'edit', 'policy.json'), 'S02'),
    (('policy', 'show'), 'S02'), (('policy', 'diff', 'policy.json'), 'S02'),
    (('approvals', 'revoke', 'apr-1'), 'S02'),
    (('prefs', 'show'), 'S03'), (('prefs', 'set', 'tone', 'brief'), 'S03'), (('prefs', 'expire', 'tone'), 'S03'),
    (('prefs', 'history'), 'S03'), (('prefs', 'rollback', '2'), 'S03'),
    (('artifact', 'register', 'chart.json'), 'S03'), (('artifact', 'show', 'art-1'), 'S03'),
    (('artifact', 'revise', 'art-1', '--change-file', 'change.json'), 'S03'), (('artifact', 'history', 'art-1'), 'S03'),
    (('memory', 'search', '--query-file', 'query.json'), 'S03'),
    (('brains', 'reindex', 'provider-1'), 'S04'),
    (('trace', 'export', 'trace-1', '--out', 'trace.json'), 'S02'), (('trace', 'replay', 'trace-1'), 'S02'),
]


@pytest.mark.parametrize(('argv', 'slice_id'), SPECIFIED_LATER, ids=[' '.join(argv) for argv, _ in SPECIFIED_LATER])
def test_n15_a_command_the_specification_names_answers_unsupported_with_its_slice(
        profile: Profile, argv, slice_id) -> None:
    """M01-FR-01: a command of a later slice is registered and typed UNSUPPORTED, never INVALID_INPUT."""
    run = profile.run(*argv, '--json')
    value = run.value
    assert run.summary[:3] == (4, 'UNAVAILABLE', 'UNSUPPORTED') and value['data'] is None, run.out
    assert f'slice {slice_id}' in value['error']['message'] and slice_id in value['next_action']
    assert run.err == '' and profile.files() == {} and not profile.data.exists()
    assert not (profile.harness / 'trace.json').exists()


def test_n15_help_lists_the_commands_of_later_slices(profile: Profile) -> None:
    run = profile.run('--help')
    assert run.code == 0
    for command in ('server', 'login', 'grants', 'spaces', 'policy', 'prefs', 'artifact', 'memory', 'brains',
                    'approvals', 'trace'):
        assert f' {command} ' in run.out, command
    assert ' revoke ' in profile.run('approvals', '--help').out
