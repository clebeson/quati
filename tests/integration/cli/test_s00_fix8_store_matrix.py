"""S00 fix round 8: PUBLIC child-process proof of the registry store, ask pre-check and receipt rules.

Findings of the third independent audit (docs/audit/S00_AUDIT3_2026-11-16.md, LOG-0044) covered here:

* X1 - M01 "Data directory" rules 1-3 for every directory of the registry store: ``capabilities/packages``
  (and ``staging``, and a package directory) that is a symlink, foreign-owned, a file or not writable is
  refused before any registry commit or audit line; nothing is written outside the data directory.
* X2 - every file of the store is a private regular file or the command that uses it is refused within
  a bounded time: the matrix {registry.json, capabilities.lock, registry.flock, audit.jsonl, a package manifest}
  x {FIFO, symlink to an outside file, hard link, mode 0644, simulated foreign owner, directory}
  x {capabilities list, describe, install-fixture --enable-fixture, disable, ask, chat turn, trace show}.
  The fixed files are refused before the command's authorization decision is logged (nothing is
  appended); a stored package is examined only after an allowed decision (M02 order row 7: a principal
  without a grant causes no access below the registry), so its refusal follows exactly one
  ``authz.decided`` line, and ``trace show``, which reads no package, is not affected by one.
* X6 - M01 "Data directory" rule 4 and M02 authorization order: a work ``ask`` (and chat turn) checks the
  store, the audit log and the caller's grant BEFORE the first model call; zero model requests, and the
  answer does not depend on what the scripted model would have done.
* X8 - a request receipt records the policy version in force (the value its policy decisions carry),
  never the constant ``s00-fixture-readonly/1``; a greeting or refusal receipt claims no proof tier.
* X11 - a signed installation record whose identifiers are not ULIDs, and a credential file with an
  extra hard link, are INVALID in ``doctor`` and ``config validate`` and UNAUTHENTICATED everywhere.
* X13 - one refusal reason per unsafe component across commands (table test).
* X15 - ``quati doctor --json`` and every receipt carry the digest of the loaded asset files.

Every test runs the public ``quati.cli.main.main`` in a fresh child process with an isolated
``QUATI_CONFIG_DIR`` / ``QUATI_DATA_DIR`` and a HARD TIMEOUT that fails the test instead of hanging.
Proof tier: L2 (deterministic, public entry). The model is the SCRIPTED FAKE registered by
``fixtures/fix7_public_runner.py``: fake-provider compatibility only, never evidence of a real
provider; the runner refuses and records every socket use. ``QUATI_ALLOW_LIVE=1`` is set only for
child processes whose transport is that scripted fake. Foreign ownership is SIMULATED with the
runner's ``foreign_inodes`` override (the uid one process observes): it proves the refusal logic,
not a real multi-user host.
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
SCRIPTED = {'QUATI_PROVIDER': 'scripted_fake_t04', 'QUATI_ALLOW_LIVE': '1'}
HARD_TIMEOUT_S = 30
WORK_TEXT = 'Find my next appointment'
READ_SCRIPT = [['classify'], ['search', 'next appointment calendar'], ['describe', 'fixtures.calendar-read'],
               ['invoke', 'fixtures.calendar-read', {'limit': 1}], ['final', 'done']]
NO_INVOKE_SCRIPT = [['classify'], ['final', 'nothing to do']]
INSTALL_MAIL = ('capabilities', 'install-fixture', 'mail-search', '--enable-fixture', '--json')
LIST = ('capabilities', 'list', '--json')
UNSAFE = (4, 'UNAVAILABLE', 'TEMPORARILY_UNAVAILABLE', 'state_dir_unsafe')
AUDIT_UNAVAILABLE = (4, 'UNAVAILABLE', 'TEMPORARILY_UNAVAILABLE', 'audit_unavailable')
OLD_POLICY_CONSTANT = 's00-fixture-readonly/1'


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
    """One isolated LOCAL profile driven only through child processes; every run has a hard timeout."""

    def __init__(self, root: Path) -> None:
        self.root, self.config, self.data = root, root / 'config', root / 'data'
        self.harness, self.outside = root / 'harness', root / 'outside'
        self.harness.mkdir()
        self.outside.mkdir()
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
        try:
            completed = subprocess.run(command, cwd=self.harness, env=self.environment(env), input=stdin,
                                       capture_output=True, check=False, timeout=HARD_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            pytest.fail(f'quati {" ".join(argv)} did not finish within {HARD_TIMEOUT_S} s (hang)')
        spy = [json.loads(line) for line in spy_log.read_text(encoding='utf-8').splitlines()] if spy_log.exists() else []
        return Run(completed, spy)

    def scripted(self, *argv: str, script: list | None = None, env: dict | None = None, stdin: bytes = b'',
                 **scenario) -> Run:
        return self.run(*argv, env={**SCRIPTED, **(env or {})}, scenario={'script': script or [], **scenario},
                        stdin=stdin)

    def ready(self) -> str:
        """Initialized profile, calendar-read enabled, a successful scripted probe and one recorded work
        ask; returns the request id of that ask."""
        assert self.run('init', '--json').code == 0
        assert self.run('capabilities', 'install-fixture', 'calendar-read', '--enable-fixture', '--json').code == 0
        probe = self.scripted('models', 'probe', '--json')
        assert (probe.code, probe.value['status']) == (0, 'SUCCEEDED'), probe.out
        asked = self.scripted('ask', WORK_TEXT, '--json', script=READ_SCRIPT)
        assert (asked.code, asked.value['data']['result_kind']) == (0, 'FIXTURE_RESULT'), asked.out
        return asked.value['data']['request_id']

    def tree(self, base: Path) -> dict:
        """Every path below ``base`` that is not a symlink: file bytes, or None for anything else."""
        return {str(path.relative_to(base)): (path.read_bytes() if path.is_file() else None)
                for path in sorted(base.rglob('*')) if not path.is_symlink()}

    def audit_bytes(self) -> bytes:
        return (self.data / 'capabilities' / 'audit.jsonl').read_bytes()

    def audit(self) -> list:
        return [json.loads(line) for line in self.audit_bytes().splitlines()]

    def registry(self) -> bytes:
        return (self.data / 'capabilities' / 'registry.json').read_bytes()

    def receipts(self) -> list:
        return sorted((self.data / 'receipts').glob('*.json'))

    def lifecycles(self) -> dict:
        listed = self.run(*LIST)
        assert listed.code == 0, listed.out
        return {item['capability_id']: item['lifecycle'] for item in listed.value['data']['capabilities']}

    def resign(self, **changes) -> None:
        """Rewrite the installation record with ``changes``, signed by the device key."""
        record = json.loads((self.config / 'identity.json').read_bytes())
        record.pop('signature')
        record.update(changes)
        key = Ed25519PrivateKey.from_private_bytes((self.config / 'device.key').read_bytes())
        canonical = json.dumps(record, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8')
        record['signature'] = base64.b64encode(key.sign(canonical)).decode('ascii')
        (self.config / 'identity.json').write_bytes(
            json.dumps(record, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8'))


@pytest.fixture
def profile(tmp_path) -> Profile:
    return Profile(tmp_path)


def assert_unsafe(run: Run, component: str) -> None:
    """The one typed refusal of an unusable store path: exit 4, component relative to the data directory."""
    assert run.summary == UNSAFE, (run.out, run.err)
    assert run.value['data'] == {'reason': 'state_dir_unsafe', 'component': component}
    assert run.value['evidence_refs'] == [] and 'internal error' not in run.err
    assert 'no work was accepted' not in run.out.lower()


OPERATIONS = {'list': 'list', 'describe': 'describe', 'install': 'install_fixture', 'disable': 'disable',
              'ask': 'ask_admission', 'chat': 'ask_admission', 'trace_show': 'trace_show'}


def store_state(profile: Profile) -> tuple[dict, list]:
    """(every path under ``capabilities`` except the audit log, the lines of the audit log)."""
    found = profile.tree(profile.data / 'capabilities')
    log = found.pop('audit.jsonl', None)
    return found, (log or b'').splitlines()


def assert_store_unchanged(profile: Profile, before: tuple[dict, list], decision: str | None = None) -> None:
    """Nothing under ``capabilities`` changed; with ``decision``, the log gained exactly the one
    ``authz.decided`` ALLOW line of that operation (the command was authorized, then refused)."""
    files, lines = store_state(profile)
    assert files == before[0] and lines[:len(before[1])] == before[1]
    added = [json.loads(line) for line in lines[len(before[1]):]]
    assert [(event['event'], event['operation'], event['decision']['verdict']) for event in added] == (
        [] if decision is None else [('authz.decided', decision, 'ALLOW')])


def no_model_or_handler(run: Run, script: list) -> None:
    assert run.kinds('request') == [] and run.kinds('handler') == [] and run.kinds('socket') == [], run.spy
    assert run.kinds('script_left') == [['script_left', len(script)]]      # the scripted model was never asked


# ----------------------------------------------------------------- X2: the private-file matrix
PACKAGE_MANIFEST = 'capabilities/packages/fixtures.calendar-read/1.0.0/capability.scs.json'
TARGETS = {'registry.json': 'capabilities/registry.json', 'capabilities.lock': 'capabilities/capabilities.lock',
           'registry.flock': 'capabilities/registry.flock', 'audit.jsonl': 'capabilities/audit.jsonl',
           'package_manifest': PACKAGE_MANIFEST}
KINDS = ('fifo', 'symlink_outside', 'hard_link', 'mode_644', 'foreign_owner', 'directory')
MATRIX_COMMANDS = ('list', 'describe', 'install', 'disable', 'ask', 'chat', 'trace_show')


def break_file(profile: Profile, relative: str, kind: str) -> dict:
    """Make one store file unsafe; return the runner scenario that goes with the fault."""
    path = profile.data / relative
    assert path.is_file() and not path.is_symlink(), relative
    if kind == 'fifo':
        path.unlink()
        os.mkfifo(path, 0o600)
    elif kind == 'symlink_outside':
        moved = profile.outside / 'moved-file'
        path.rename(moved)
        path.symlink_to(moved)
    elif kind == 'hard_link':
        os.link(path, profile.outside / 'second-name')
    elif kind == 'mode_644':
        path.chmod(0o644)
    elif kind == 'foreign_owner':             # what a file of another user looks like by path and by descriptor
        return {'foreign_inodes': [str(path)], 'foreign_paths': [str(path)]}
    else:
        path.unlink()
        path.mkdir(mode=0o700)
    return {}


def matrix_command(profile: Profile, name: str, request_id: str, scenario: dict) -> tuple[Run, list]:
    if name == 'list':
        return profile.scripted(*LIST, **scenario), []
    if name == 'describe':
        return profile.scripted('capabilities', 'describe', 'fixtures.calendar-read', '--json', **scenario), []
    if name == 'install':
        return profile.scripted(*INSTALL_MAIL, **scenario), []
    if name == 'disable':
        return profile.scripted('capabilities', 'disable', 'fixtures.calendar-read@1.0.0', '--json', **scenario), []
    if name == 'ask':
        return profile.scripted('ask', WORK_TEXT, '--json', script=READ_SCRIPT, **scenario), READ_SCRIPT
    if name == 'chat':
        return profile.scripted('chat', '--jsonl', script=READ_SCRIPT, stdin=(WORK_TEXT + '\n').encode(),
                                **scenario), READ_SCRIPT
    return profile.scripted('trace', 'show', request_id, '--json', **scenario), []


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('target', list(TARGETS))
def test_x2_every_store_file_is_private_or_every_command_refuses_in_bounded_time(
        profile: Profile, target: str, kind: str) -> None:
    """M01 "Data directory" rules 2 and 4: one typed refusal per unsafe file, for every command that uses
    it, with no model call, no handler, no registry change and nothing touched outside the data directory."""
    request_id = profile.ready()
    relative = TARGETS[target]
    scenario = break_file(profile, relative, kind)
    for name in MATRIX_COMMANDS:
        before, outside = store_state(profile), profile.tree(profile.outside)
        receipts = len(profile.receipts())
        run, script = matrix_command(profile, name, request_id, scenario)
        label = f'{target} as {kind}: {name}'
        no_model_or_handler(run, script)
        assert profile.tree(profile.outside) == outside, label
        if target == 'package_manifest' and name == 'trace_show':
            # A trace reads receipts and the audit log, never a package: it is answered (M26 S00 form).
            assert (run.code, run.value['data']['request_id']) == (0, request_id), label
            assert_store_unchanged(profile, before, 'trace_show')
        elif target == 'package_manifest':            # examined after the allowed decision, before any read
            assert_unsafe(run, relative)
            assert run.code == 4 and len(profile.receipts()) == receipts, label
            assert_store_unchanged(profile, before, OPERATIONS[name])
        elif target != 'audit.jsonl':                 # a fixed store file: refused before the decision
            assert_unsafe(run, relative)
            assert run.code == 4 and len(profile.receipts()) == receipts, label      # chat: the session ends with 4
            assert_store_unchanged(profile, before)
        elif name == 'trace_show':                    # M26 S00 form, check 5: the log a trace reads
            assert run.summary == (4, 'UNAVAILABLE', 'TEMPORARILY_UNAVAILABLE', 'audit_store_unavailable'), label
            assert store_state(profile) == before, label
        else:                                         # M01 "Data directory" rule 4
            assert store_state(profile) == before, label
            value = run.value
            assert (value['status'], value['error']['code'], value['data']['reason']) == AUDIT_UNAVAILABLE[1:], label
            assert run.code == (0 if name == 'chat' else 4), label      # a refused turn does not end the session
            if name in ('ask', 'chat'):               # refused before the model path, with its request receipt
                assert value['data']['provider_used'] is False and value['data']['result_kind'] == 'BLOCKED'
                assert len(value['evidence_refs']) == 1 and len(profile.receipts()) == receipts + 1, label


# ----------------------------------------------------------------- X1: the store directories
def break_directory(profile: Profile, relative: str, kind: str) -> dict:
    path = profile.data / relative
    if kind == 'symlink':
        moved = profile.outside / 'moved-directory'
        if path.exists():
            path.rename(moved)
        else:
            moved.mkdir(mode=0o700)
        path.symlink_to(moved, target_is_directory=True)
    elif kind == 'foreign_owner':
        return {'foreign_inodes': [str(path)], 'foreign_paths': [str(path)]}
    elif kind == 'file':
        for item in sorted(path.rglob('*'), reverse=True):
            item.rmdir() if item.is_dir() else item.unlink()
        path.rmdir()
        path.write_bytes(b'not a directory')
        path.chmod(0o600)
    else:
        path.chmod(0o500)
    return {}


@pytest.mark.parametrize('kind', ['symlink', 'foreign_owner', 'file', 'mode_500'])
def test_x1_an_unusable_packages_directory_refuses_the_install_before_any_commit(profile: Profile, kind: str) -> None:
    """The audit's four cases: no registry revision, no audit event, nothing written through a symlink
    or into a foreign-owned directory, and never a failure reported after a commit."""
    profile.ready()
    scenario = break_directory(profile, 'capabilities/packages', kind)
    registry, audit, outside = profile.registry(), profile.audit_bytes(), profile.tree(profile.outside)
    receipts = len(profile.receipts())
    run = profile.scripted(*INSTALL_MAIL, **scenario)
    assert_unsafe(run, 'capabilities/packages')
    assert json.loads(profile.registry())['revision'] == json.loads(registry)['revision']
    assert profile.registry() == registry and profile.audit_bytes() == audit
    assert profile.tree(profile.outside) == outside and len(profile.receipts()) == receipts
    assert 'mail-search' not in json.dumps(json.loads(profile.registry()))
    listed = profile.scripted(*LIST, **scenario)       # the same refusal for a read: one reason per component
    assert_unsafe(listed, 'capabilities/packages')
    if kind == 'mode_500':                             # repaired by the user: the same install then succeeds
        (profile.data / 'capabilities' / 'packages').chmod(0o700)
        assert profile.run(*INSTALL_MAIL).code == 0
        assert profile.lifecycles() == {'fixtures.calendar-read': 'ENABLED', 'fixtures.mail-search': 'ENABLED'}
        assert (profile.data / 'capabilities' / 'packages' / 'fixtures.mail-search' / '1.0.0').is_dir()


@pytest.mark.parametrize(('relative', 'kind'), [
    ('capabilities/staging', 'symlink'), ('capabilities/staging', 'foreign_owner'),
    ('capabilities/packages/fixtures.calendar-read', 'symlink'),
    ('capabilities/packages/fixtures.calendar-read/1.0.0', 'symlink'),
    ('capabilities/packages/fixtures.calendar-read/1.0.0', 'foreign_owner')])
@pytest.mark.parametrize('name', ['install', 'list', 'ask'])
def test_x1_every_sub_directory_of_the_store_is_verified_before_use(
        profile: Profile, name: str, relative: str, kind: str) -> None:
    """M01 "Data directory" rule 1: ``capabilities`` AND its sub-directories, down to a package version.
    ``staging`` is verified before the decision is logged; a package directory after the allowed decision
    and before the first registry read, lock or write."""
    request_id = profile.ready()
    scenario = break_directory(profile, relative, kind)
    before, outside = store_state(profile), profile.tree(profile.outside)
    registry = profile.registry()
    run, script = matrix_command(profile, name, request_id, scenario)
    assert_unsafe(run, relative)
    no_model_or_handler(run, script)
    assert (profile.registry(), profile.tree(profile.outside)) == (registry, outside)
    assert_store_unchanged(profile, before, None if relative == 'capabilities/staging' else OPERATIONS[name])


def test_x1_a_successful_install_leaves_no_staging_copy_and_a_private_tree(profile: Profile) -> None:
    """The positive leg of the ordering: publish, lock entry, registry and audit agree after the command."""
    profile.ready()
    run = profile.run(*INSTALL_MAIL)
    assert (run.code, run.value['status'], run.value['data']['lifecycle']) == (0, 'SUCCEEDED', 'ENABLED')
    root = profile.data / 'capabilities'
    assert (root / 'packages' / 'fixtures.mail-search' / '1.0.0' / 'capability.scs.json').is_file()
    assert list((root / 'staging').iterdir()) == []
    lock = json.loads((root / 'capabilities.lock').read_bytes())
    assert [entry['id'] for entry in lock['entries']] == ['fixtures.calendar-read', 'fixtures.mail-search']
    wrong = [str(path) for path in [root, *root.rglob('*')]
             if stat.S_IMODE(path.lstat().st_mode) != (0o700 if path.is_dir() else 0o600)]
    assert wrong == []


# ----------------------------------------------------------------- X6: checks before the first model call
def torn_audit(profile: Profile) -> None:
    log = profile.data / 'capabilities' / 'audit.jsonl'
    log.write_bytes(log.read_bytes() + b'{"event": "torn')


@pytest.mark.parametrize('script', [READ_SCRIPT, NO_INVOKE_SCRIPT], ids=['model_would_invoke', 'model_would_not'])
@pytest.mark.parametrize('command', ['ask', 'chat'])
def test_x6_a_torn_audit_log_refuses_the_ask_before_the_first_model_call(profile: Profile, command, script) -> None:
    """Rule 4: ``audit_unavailable`` with zero model requests, whatever the model would have done."""
    profile.ready()
    torn_audit(profile)
    audit, registry = profile.audit_bytes(), profile.registry()
    if command == 'ask':
        run = profile.scripted('ask', WORK_TEXT, '--json', script=script)
    else:
        run = profile.scripted('chat', '--jsonl', script=script, stdin=(WORK_TEXT + '\n').encode())
    value = run.value
    assert (value['status'], value['error']['code'], value['data']['reason']) == AUDIT_UNAVAILABLE[1:], run.out
    assert run.code == (4 if command == 'ask' else 0)
    assert value['data']['result_kind'] == 'BLOCKED' and value['data']['provider_used'] is False
    assert value['data']['tool_calls'] == [] and len(value['evidence_refs']) == 1
    no_model_or_handler(run, script)
    assert (profile.audit_bytes(), profile.registry()) == (audit, registry)      # nothing appended


@pytest.mark.parametrize('role', ['GUEST', 'not-a-role'])
@pytest.mark.parametrize('command', ['ask', 'chat'])
def test_x6_a_principal_without_a_registry_grant_is_refused_before_the_first_model_call(
        profile: Profile, command: str, role: str) -> None:
    """M02 order rows 4 and 7: typed ``NO_SPACE_GRANT``, logged once, zero model requests."""
    profile.ready()
    profile.resign(tenant_role=role)
    events = len(profile.audit())
    if command == 'ask':
        run = profile.scripted('ask', WORK_TEXT, '--json', script=READ_SCRIPT)
    else:
        run = profile.scripted('chat', '--jsonl', script=READ_SCRIPT, stdin=(WORK_TEXT + '\n').encode())
    value = run.value
    assert (value['status'], value['error']['code'], value['data']['reason']) == (
        'DENIED', 'FORBIDDEN', 'NO_SPACE_GRANT'), run.out
    assert run.code == (4 if command == 'ask' else 0)
    assert value['data']['result_kind'] == 'BLOCKED' and value['data']['provider_used'] is False
    assert value['data']['tool_calls'] == [] and len(value['evidence_refs']) == 1
    no_model_or_handler(run, READ_SCRIPT)
    added = profile.audit()[events:]
    assert [(event['event'], event['operation'], event['decision']['action'], event['decision']['verdict'],
             event['decision']['reason_code']) for event in added] == [
        ('authz.decided', 'ask_admission', 'read', 'DENY', 'NO_SPACE_GRANT')]
    assert added[0]['request_id'] == value['data']['request_id']


def test_x6_a_member_with_a_grant_is_admitted_and_a_guest_is_still_greeted(profile: Profile) -> None:
    """The admission check denies nobody who holds the grant; social-only text uses no registry at all."""
    profile.ready()
    profile.resign(tenant_role='MEMBER')
    events = len(profile.audit())
    run = profile.scripted('ask', WORK_TEXT, '--json', script=READ_SCRIPT)
    # A MEMBER holds the grant: the ask is admitted and reaches the model (what the policy gate then
    # decides for a MEMBER is M25's rule, not the admission check's).
    assert run.value['data']['reason'] != 'NO_SPACE_GRANT' and len(run.kinds('request')) > 0, run.out
    assert run.value['data']['provider_used'] is True
    first = profile.audit()[events]
    assert (first['event'], first['operation'], first['decision']['verdict']) == (
        'authz.decided', 'ask_admission', 'ALLOW')
    profile.resign(tenant_role='GUEST')
    audit = profile.audit_bytes()
    greeted = profile.scripted('ask', 'hello', '--json', script=READ_SCRIPT)
    assert (greeted.code, greeted.value['data']['result_kind']) == (0, 'GREETING')
    no_model_or_handler(greeted, READ_SCRIPT)
    assert profile.audit_bytes() == audit


# ----------------------------------------------------------------- X13: one reason per unsafe component
def run_named(profile: Profile, command: str) -> tuple[Run, list]:
    if command == 'probe':
        return profile.scripted('models', 'probe', '--json'), []
    if command == 'doctor_probe':
        return profile.scripted('doctor', '--probe', '--json'), []
    return matrix_command(profile, command, 'request-' + '0' * 32, {})


REASON_TABLE = [(component, fault, command)
                for component, commands in (
                    ('feature_reports', ('ask', 'chat', 'probe', 'doctor_probe')),
                    ('capabilities', ('ask', 'chat', 'probe', 'doctor_probe', 'list', 'install', 'trace_show')),
                    ('receipts', ('ask', 'chat', 'probe', 'doctor_probe', 'install', 'trace_show')))
                for fault in ('symlink', 'file')
                for command in commands]


@pytest.mark.parametrize(('component', 'fault', 'command'), REASON_TABLE,
                         ids=[f'{component}-{fault}-{command}' for component, fault, command in REASON_TABLE])
def test_x13_an_unsafe_directory_has_one_reason_in_every_command(profile: Profile, component, fault, command) -> None:
    """``state_dir_unsafe`` naming the component, before any provider call: never ``MODEL_INCOMPATIBLE``
    with advice to probe (the probe would refuse too), never ``audit_unavailable`` for a directory."""
    profile.ready()
    break_directory(profile, component, fault)
    outside = profile.tree(profile.outside)
    run, script = run_named(profile, command)
    assert_unsafe(run, component)
    no_model_or_handler(run, script)
    assert run.kinds('probe_call') == [] and profile.tree(profile.outside) == outside


def test_x13_a_permissive_feature_report_directory_is_not_reported_as_an_incompatible_model(profile: Profile) -> None:
    """A reader modifies nothing: mode 0755 is refused for ``ask`` with the reason the probe's storage has."""
    profile.ready()
    (profile.data / 'feature_reports').chmod(0o755)
    run = profile.scripted('ask', WORK_TEXT, '--json', script=READ_SCRIPT)
    assert_unsafe(run, 'feature_reports')
    no_model_or_handler(run, READ_SCRIPT)
    assert stat.S_IMODE((profile.data / 'feature_reports').stat().st_mode) == 0o755
    assert profile.scripted('models', 'probe', '--json').code == 0      # the writer removes the wider bits
    assert stat.S_IMODE((profile.data / 'feature_reports').stat().st_mode) == 0o700
    assert profile.scripted('ask', WORK_TEXT, '--json', script=READ_SCRIPT).code == 0


# ----------------------------------------------------------------- X8: the policy reference of a receipt
def receipt_of(value: dict) -> dict:
    return json.loads(Path(value['evidence_refs'][0].split(':', 2)[2]).read_bytes())


def test_x8_receipts_record_the_policy_version_in_force_and_no_test_proof_tier(profile: Profile) -> None:
    """The receipt, its policy decisions and its prompt digest name ONE policy; no constant, no ``L1``."""
    request_id = profile.ready()
    work = next(json.loads(path.read_bytes()) for path in profile.receipts()
                if json.loads(path.read_bytes()).get('request_id') == request_id)
    decisions = [event['decision']['policy_version'] for event in profile.audit()
                 if event['event'] == 'policy.decided' and event['request_id'] == request_id]
    assert len(decisions) == 1 and len(decisions[0]) == 64
    assert work['policy_version'] == decisions[0] == work['digests']['policy_ref'].rsplit('@', 1)[1]
    shown = profile.run('trace', 'show', request_id, '--json').value['data']
    assert shown['receipt']['policy_version'] == shown['policy_decisions'][0]['policy_version'] == decisions[0]
    greeting = profile.run('ask', 'hello', '--json')
    refusal = profile.run('ask', WORK_TEXT, '--json')                 # no provider configured: exit 3
    assert (greeting.code, refusal.code) == (0, 3)
    for run in (greeting, refusal):
        receipt = receipt_of(run.value)
        assert receipt['policy_version'] == decisions[0] and receipt['proof_tier'] is None
    for path in profile.receipts():
        assert OLD_POLICY_CONSTANT not in path.read_text(encoding='utf-8')


def test_x8_without_an_installed_policy_the_receipt_names_the_kernel_baseline(profile: Profile) -> None:
    """No policy file: the version in force is the kernel baseline digest (what a decision would carry)."""
    from quati.domain.policy import KERNEL_BASELINE_VERSION
    assert profile.run('init', '--json').code == 0
    (profile.config / 'policy.json').unlink()
    run = profile.run('ask', 'hello', '--json')
    assert run.code == 0 and receipt_of(run.value)['policy_version'] == KERNEL_BASELINE_VERSION


# ----------------------------------------------------------------- X11: identity shape and hard links
@pytest.mark.parametrize('field', ['tenant_id', 'principal_id', 'personal_space_id', 'organization_space_id'])
@pytest.mark.parametrize('value', ['../../../x', 'has a space', 'x' * 10000, '01ARZ3NDEKTSV4RRFFQ69G5FAI'])
def test_x11_a_signed_record_with_a_non_ulid_identifier_is_invalid_everywhere(profile: Profile, field, value) -> None:
    """contracts/identity.schema.json LocalInstallationRecord: every identifier is a ULID."""
    assert profile.run('init', '--json').code == 0
    profile.resign(**{field: value})
    doctor = profile.run('doctor', '--json')
    identity = doctor.value['data']['identity']
    assert doctor.code == 0 and (identity['status'], identity['reason'], identity['detail']) == (
        'INVALID', 'credential_corrupt', 'record_rejected')
    validate = profile.run('config', 'validate', '--json')
    checks = {check['name']: check for check in validate.value['data']['checks']}
    assert validate.code == 2 and checks['identity']['status'] == 'INVALID'
    assert checks['identity']['reasons'] == ['credential_corrupt', 'record_rejected']
    for argv in (('ask', 'hello', '--json'), LIST):
        assert profile.run(*argv).summary == (4, 'DENIED', 'UNAUTHENTICATED', None)


@pytest.mark.parametrize(('name', 'detail'), [('identity.json', 'identity_file_hard_link'),
                                              ('device.key', 'device_key_hard_link')])
def test_x11_a_credential_file_with_an_extra_hard_link_is_rejected(profile: Profile, name: str, detail: str) -> None:
    assert profile.run('init', '--json').code == 0
    os.link(profile.config / name, profile.outside / 'second-name')
    doctor = profile.run('doctor', '--json')
    identity = doctor.value['data']['identity']
    assert (identity['status'], identity['reason'], identity['detail']) == ('INVALID', 'credential_insecure', detail)
    validate = profile.run('config', 'validate', '--json')
    assert validate.code == 2
    for argv in (('ask', 'hello', '--json'), LIST):
        assert profile.run(*argv).summary == (4, 'DENIED', 'UNAUTHENTICATED', None)
    (profile.outside / 'second-name').unlink()
    assert profile.run('ask', 'hello', '--json').code == 0


# ----------------------------------------------------------------- X15: the asset digest is observable
def test_x15_doctor_and_every_receipt_carry_the_digest_of_the_loaded_assets(profile: Profile) -> None:
    from quati.behavior import contracts
    expected = contracts.asset_digest()
    assert len(expected) == 64
    request_id = profile.ready()
    doctor = profile.run('doctor', '--json').value['data']
    assert doctor['behavior']['status'] == 'VALID' and doctor['behavior']['asset_digest'] == expected
    receipts = [json.loads(path.read_bytes()) for path in profile.receipts()]
    assert len(receipts) >= 4                      # init policy event, install, feature report, ask
    for receipt in receipts:
        assert receipt['digests']['asset_digest'] == expected and len(receipt['digests']['code_digest']) == 64
    shown = profile.run('trace', 'show', request_id, '--json').value['data']['receipt']['digests']
    assert shown['asset_digest'] == expected
