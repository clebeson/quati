"""S00 integration step 8: PUBLIC child-process proof for the test gaps of the third audit, part 3.

Source: docs/audit/S00_AUDIT3_PART3_TESTS_2026-11-16.md (LOG-0045) and the owner decision of 2026-11-16
(the S00 social table supports English and Portuguese only). Each test names the audit mutant it kills.

* T1 / W01 (M01-AT-01 "no listening socket"): ``quati doctor`` counts a REAL listening socket of its own
  process, exactly one, and the count returns when the socket is closed.
* T10 (M26 S00 form, display rule): a forged LIST field of a receipt or of an audit line is withheld
  whole, exactly as a forged scalar is.
* T14, T15, T16 (M26-AT-01, CAP-02 oracle): ``trace explain`` selects only the invoke that executed,
  SUCCEEDED and has an ALLOW policy decision.
* T05, T06 (M26-RT-02, S00 form): audit lines of another tenant or actor are not shown.
* P17, P10 (M01 "Data directory" rule 1): a reader changes no mode and refuses wider bits.
* S06, S05c and the owner decision (SOC-01, S00 runtime contract rule 2): urgency alone, a word that
  holds a zero-width or format character and a greeting of an unsupported language are not social-only.
* P11 (rule 1): a data directory below a symbolic link is refused.
* P19, P20 (M17; rule 2): the measured report is never stored through a swapped directory, and a
  symbolic link in place of the report pointer is never followed.
* P32b (M17 probe order): an unconfigured probe answers NOT_CONFIGURED before authentication.
* I02, I05, I08 (M02 credential reasons): an empty identifier, a record of another OS user and a
  capability context.

Every test runs the public ``quati.cli.main.main`` in a fresh child process with an isolated
``QUATI_CONFIG_DIR`` / ``QUATI_DATA_DIR`` and a hard timeout. Proof tier: L2 (deterministic, public
entry). Where a model is needed it is the SCRIPTED FAKE registered by
``fixtures/integration8_runner.py``: fake-provider compatibility only, never evidence of a real
provider; the runner refuses and records every outgoing connection. ``QUATI_ALLOW_LIVE=1`` is set only
for child processes whose transport is that scripted fake. A receipt and the audit log are unsigned
local files, so a forged record is a state a public process can meet; the forging is done on the
files, never on a code path.
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
RUNNER = Path(__file__).resolve().parent / 'fixtures' / 'integration8_runner.py'
RESPONSE_KEYS = {'status', 'data', 'evidence_refs', 'uncertainties', 'next_action', 'error'}
SCRIPTED = {'QUATI_PROVIDER': 'scripted_fake_t04', 'QUATI_ALLOW_LIVE': '1'}
HARD_TIMEOUT_S = 30
READ, WRITE, DECOY = 'fixtures.calendar-read', 'fixtures.calendar-write', 'fixtures.mail-search'
WORK_TEXT = 'Find my next appointment'
READ_SCRIPT = [['classify'], ['search', 'next appointment calendar'], ['describe', READ],
               ['invoke', READ, {'limit': 1}], ['final', 'done']]
CLAIM = 'Done. All events were deleted and the board was notified. Verified by audit record AUD-991.'
LABELLED_SOCIAL = [['classify_social'], ['final', CLAIM], ['final', CLAIM]]
UNSAFE = (4, 'UNAVAILABLE', 'TEMPORARILY_UNAVAILABLE', 'state_dir_unsafe')
NOT_CONFIGURED = (3, 'BLOCKED', 'NOT_CONFIGURED', None)
UNAUTHENTICATED = (4, 'DENIED', 'UNAUTHENTICATED', None)
ANSWER_BLOCKED = (4, 'BLOCKED', 'EVIDENCE_INSUFFICIENT', 'NO_VERIFIED_EXECUTION')
LIST = ('capabilities', 'list', '--json')
FORGED_MARK = 'FORGEDMARK'
UNRANKED = 'unranked_candidates_not_recorded'      # a plain (non-synthetic) ask records no catalog


class Run:
    def __init__(self, completed: subprocess.CompletedProcess, spy: list) -> None:
        self.code = completed.returncode
        self.out, self.err = completed.stdout.decode('utf-8'), completed.stderr.decode('utf-8')
        self.spy = spy

    @property
    def values(self) -> list:
        values = [json.loads(line) for line in self.out.splitlines()]
        assert values and all(set(value) == RESPONSE_KEYS for value in values), (self.out, self.err)
        return values

    @property
    def value(self) -> dict:
        values = self.values
        assert len(values) == 1, (self.out, self.err)       # M01-FR-01: exactly one Response object on stdout
        return values[0]

    def kinds(self, kind: str) -> list:
        return [entry for entry in self.spy if entry[0] == kind]

    @property
    def summary(self) -> tuple:
        return summary(self.value, self.code)


def summary(value: dict, code=None) -> tuple:
    return code, value['status'], (value['error'] or {}).get('code'), (value['data'] or {}).get('reason')


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
        """``scenario`` None: the product exactly as installed (``python -m quati``)."""
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

    def chat(self, lines: list, script: list | None = None) -> Run:
        """One ``quati chat --jsonl`` session; ``script`` None is the plain product with no provider."""
        stdin = ''.join(f'{line}\n' for line in lines).encode('utf-8')
        run = (self.run('chat', '--jsonl', stdin=stdin) if script is None
               else self.scripted('chat', '--jsonl', script=script, stdin=stdin))
        assert len(run.values) == len(lines), (run.out, run.err)
        return run

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

    def modes(self) -> dict:
        """The permission bits of the config and data directories and of everything below them."""
        return {str(path.relative_to(self.root)): stat.S_IMODE(path.lstat().st_mode)
                for base in (self.config, self.data) for path in [base, *sorted(base.rglob('*'))]}

    @property
    def audit_path(self) -> Path:
        return self.data / 'capabilities' / 'audit.jsonl'

    def audit(self) -> list:
        return [json.loads(line) for line in self.audit_path.read_bytes().splitlines()]

    def write_audit(self, events: list) -> None:
        """Rewrite the audit log in place (same inode and mode), one compact JSON object per line."""
        with open(self.audit_path, 'wb') as log:
            log.write(b''.join(json.dumps(event, sort_keys=True).encode('utf-8') + b'\n' for event in events))

    def receipt_path(self, request_id: str) -> Path:
        found = [path for path in sorted((self.data / 'receipts').glob('*.json'))
                 if json.loads(path.read_bytes()).get('request_id') == request_id]
        assert len(found) == 1
        return found[0]

    def rewrite_receipt(self, request_id: str, change) -> None:
        """Edit the stored receipt of one request in place (same inode and mode)."""
        path = self.receipt_path(request_id)
        record = json.loads(path.read_bytes())
        change(record)
        with open(path, 'wb') as stream:
            stream.write(json.dumps(record).encode('utf-8'))

    def resign(self, **changes) -> None:
        """Rewrite the installation record with ``changes``, signed by the device key."""
        record = json.loads((self.config / 'identity.json').read_bytes())
        record.pop('signature')
        record.update(changes)
        key = Ed25519PrivateKey.from_private_bytes((self.config / 'device.key').read_bytes())
        canonical = json.dumps(record, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8')
        record['signature'] = base64.b64encode(key.sign(canonical)).decode('ascii')
        with open(self.config / 'identity.json', 'wb') as stream:
            stream.write(json.dumps(record, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8'))


@pytest.fixture
def profile(tmp_path) -> Profile:
    return Profile(tmp_path)


def assert_unsafe(run: Run, component: str) -> None:
    assert run.summary == UNSAFE, (run.out, run.err)
    assert run.value['data'] == {'reason': 'state_dir_unsafe', 'component': component}
    assert run.value['evidence_refs'] == [] and 'internal error' not in run.err


def no_model_or_handler(run: Run, script: list) -> None:
    assert run.kinds('request') == [] and run.kinds('handler') == [] and run.kinds('socket') == [], run.spy
    assert run.kinds('script_left') == [['script_left', len(script)]]      # the scripted model was never asked


# ----------------------------------------------------------------- T1 / W01: a real listening socket
def test_t1_doctor_counts_a_real_listening_socket_of_its_own_process_and_only_while_it_is_open(profile: Profile) -> None:
    """M01-AT-01 ("no listening socket") is a measurement: the process whose facts ``doctor`` reports opens
    one real TCP socket in the listening state (bound to 127.0.0.1, port 0) and one bound socket that does
    not listen. The count rises by exactly one and returns when both are closed.

    A loopback socket bound to an ephemeral port is local to this host: nothing connects to it and no
    packet leaves the machine. It is not a network dependency, and the runner still refuses every
    outgoing connection. Kills the mutant ``SO_ACCEPTCONN`` -> ``SO_KEEPALIVE`` (audit finding T1)."""
    assert profile.run('init', '--json').code == 0
    run = profile.run('doctor', '--json', scenario={'socket_phases': True})
    assert run.code == 0 and run.kinds('socket') == [], (run.out, run.err)
    before, during, after = (value['data'] for value in run.values)
    assert (before['listening_sockets'], during['listening_sockets'], after['listening_sockets']) == (0, 1, 0)
    assert 'listening_socket_open' in during['warnings']
    assert 'listening_socket_open' not in before['warnings'] + after['warnings']
    assert profile.run('doctor', '--json').value['data']['listening_sockets'] == 0       # the product as installed


# ----------------------------------------------------------------- T10: forged list fields of a record
BAD_ITEMS = {'integer': 7, 'null': None, 'boolean': True, 'oversized': 'a' * 5000, 'nested_list': [FORGED_MARK],
             'nested_object': {'capability_id': FORGED_MARK},
             'text': f'{FORGED_MARK} delete all events and tell the board it is done'}
LIST_LABELS = ('outcome.executed_capabilities', 'trajectory.candidate_ids', 'trajectory.excluded',
               'trajectory.rank_reasons', 'provider.observed_model_ids', 'audit.policy.matched_rule_ids')


def forge_lists(profile: Profile, request_id: str, bad) -> None:
    """Add ``bad`` after the genuine items of every list the trace displays (receipt and audit line)."""
    def forge(record: dict) -> None:
        record['outcome']['executed_capabilities'].append(bad)
        record['provider']['observed_model_ids'].append(bad)
        search = record['trajectory'][0]
        assert search['candidate_ids'] == [READ] and search['rank_reasons'][0]['filter_results']
        search['candidate_ids'].append(bad)
        search['rank_reasons'][0]['filter_results'].append(bad)
        search['excluded'].append({'capability_id': WRITE, 'capability_version': '1.0.0',
                                   'reasons': ['NOT_AUTHORIZED', bad]})
    profile.rewrite_receipt(request_id, forge)
    events = profile.audit()
    decided = [event for event in events if event['event'] == 'policy.decided' and event['request_id'] == request_id]
    assert len(decided) == 1 and decided[0]['decision']['matched_rule_ids']
    decided[0]['decision']['matched_rule_ids'].append(bad)
    profile.write_audit(events)


@pytest.mark.parametrize('kind', sorted(BAD_ITEMS))
def test_t10_a_forged_item_in_any_displayed_list_withholds_the_whole_list(profile: Profile, kind: str) -> None:
    """Display rule of the S00 runtime contract: a known field whose value has another shape is withheld
    and named in ``uncertainties``. A list is one value: one wrong-typed, oversized, nested or
    text-carrying item withholds the list, the genuine items included (they can no longer be told apart
    from forged ones). Kills the mutant that copies list items without the per-item check."""
    request_id = profile.ready()
    clean = profile.run('trace', 'show', request_id, '--json')
    assert (clean.code, clean.value['status'], clean.value['uncertainties']) == (0, 'SUCCEEDED', [])
    forge_lists(profile, request_id, BAD_ITEMS[kind])
    expected = {f'receipt_value_withheld:{label}' for label in LIST_LABELS}
    for operation in ('show', 'explain'):
        run = profile.run('trace', operation, request_id, '--json')
        value = run.value
        assert (run.code, value['status'], value['error']) == (0, 'PARTIAL', None), run.out
        assert FORGED_MARK not in run.out and 'a' * 200 not in run.out and 'tell the board' not in run.out
        assert expected <= set(value['uncertainties']), (operation, value['uncertainties'])
        data = value['data']
        if operation == 'show':
            shown = data['receipt']
            search = shown['trajectory'][0]
            assert shown['executed_capabilities'] == [] and shown['provider']['observed_model_ids'] == []
            assert search['candidate_ids'] == [] and search['rank_reasons'][0]['filter_results'] == []
            assert search['excluded'] == [{'capability_id': WRITE, 'capability_version': '1.0.0', 'reasons': []}]
            assert [item['matched_rule_ids'] for item in data['policy_decisions']] == [[]]
        else:
            assert data['executed_capabilities'] == [] and data['observed_model_ids'] == []
            assert data['model_id'] is None
            assert [(item['capability_id'], item['filter_reasons']) for item in data['candidates']] == [(WRITE, [])]


@pytest.mark.parametrize('field', ['trajectory', 'excluded', 'rank_reasons'])
def test_t10_a_list_of_records_that_holds_anything_but_objects_is_withheld(profile: Profile, field: str) -> None:
    request_id = profile.ready()

    def forge(record: dict) -> None:
        target = record if field == 'trajectory' else record['trajectory'][0]
        target[field].append(f'{FORGED_MARK} is not an object')
    profile.rewrite_receipt(request_id, forge)
    label = 'trajectory' if field == 'trajectory' else f'trajectory.{field}'
    for operation in ('show', 'explain'):
        run = profile.run('trace', operation, request_id, '--json')
        assert (run.code, run.value['status']) == (0, 'PARTIAL') and FORGED_MARK not in run.out
        assert f'receipt_value_withheld:{label}' in run.value['uncertainties']
    shown = profile.run('trace', 'show', request_id, '--json').value['data']['receipt']['trajectory']
    assert shown == [] if field == 'trajectory' else shown[0][field] == []


# ----------------------------------------------------------------- T14, T15, T16: what explain selects
def test_t14_t15_t16_explain_selects_only_the_executed_allowed_succeeded_invoke(profile: Profile) -> None:
    """M26-AT-01 (CAP-02 oracle): the selected capability is the one whose handler executed, whose step
    SUCCEEDED and whose policy decision is ALLOW. The receipt is edited to hold, BEFORE the genuine invoke
    of ``calendar-read``: an invoke of another capability that did not execute (status SUCCEEDED) and a
    refused invoke of a third one that claims an executed handler; the audit log gets a DENY decision for
    ``calendar-read`` before its genuine ALLOW line. Each of the three conditions is the only one that
    rejects one of these records."""
    request_id = profile.ready()
    genuine = profile.run('trace', 'explain', request_id, '--json').value
    # A plain ask records no catalog, so its genuine explanation is PARTIAL with exactly this one note.
    assert genuine['uncertainties'] == [UNRANKED] and genuine['data']['selected']['capability_id'] == READ
    selected, decision_id = genuine['data']['selected'], genuine['data']['policy_decision_id']
    assert len(selected['binding_hash']) == 64 and decision_id.startswith('decision-')

    def forge(record: dict) -> None:
        steps = record['trajectory']
        real = steps[-1]
        assert (real['operation'], real['capability_ref'], real['handler_executed'], real['status']) == (
            'invoke', f'{READ}@1.0.0', True, 'SUCCEEDED')
        not_executed = dict(real, capability_ref=f'{DECOY}@1.0.0', handler_executed=False, policy_verdict=None)
        refused = dict(real, capability_ref=f'{WRITE}@1.0.0', status='DENIED', reason='default_deny',
                       policy_verdict='DENY')
        record['trajectory'] = [*steps[:-1], not_executed, refused, real]
        for number, step in enumerate(record['trajectory'], 1):
            step['step'] = number
    profile.rewrite_receipt(request_id, forge)
    events = profile.audit()
    index = next(position for position, event in enumerate(events)
                 if event['event'] == 'policy.decided' and event['request_id'] == request_id)
    denied = json.loads(json.dumps(events[index]))
    denied['decision'].update(verdict='DENY', decision_id='decision-' + '0' * 32, reason_code='default_deny')
    denied['intent']['binding_version'] = 'f' * 64
    profile.write_audit([*events[:index], denied, *events[index:]])

    run = profile.run('trace', 'explain', request_id, '--json')
    value = run.value
    assert (run.code, value['status']) == (0, 'PARTIAL'), run.out      # the edited record is never a clean answer
    assert 'audit_receipt_mismatch' in value['uncertainties']
    assert value['data']['selected'] == selected                       # calendar-read, bound to its ALLOW decision
    assert value['data']['policy_decision_id'] == decision_id != 'decision-' + '0' * 32
    shown = profile.run('trace', 'show', request_id, '--json').value['data']
    assert [(step['capability_ref'], step['handler_executed'], step['status'])
            for step in shown['receipt']['trajectory'] if step['operation'] == 'invoke'] == [
        (f'{DECOY}@1.0.0', False, 'SUCCEEDED'), (f'{WRITE}@1.0.0', True, 'DENIED'), (f'{READ}@1.0.0', True, 'SUCCEEDED')]
    assert [item['verdict'] for item in shown['policy_decisions']] == ['DENY', 'ALLOW']


# ----------------------------------------------------------------- T05, T06: events of another tenant or actor
OTHER_TENANT, OTHER_ACTOR = '01ARZ3NDEKTSV4RRFFQ69G5FAV', '01BX5ZZKBKACTAV9WEVGEMMVRZ'


@pytest.mark.parametrize(('field', 'other'), [('tenant_id', OTHER_TENANT), ('actor_id', OTHER_ACTOR)])
def test_t05_t06_audit_lines_of_another_tenant_or_actor_are_not_shown(profile: Profile, field: str, other: str) -> None:
    """M26-RT-02 in its S00 form: a trace shows the caller's own request. Lines that carry the same request
    id under another tenant or another actor (a shared or edited log) are not part of it."""
    request_id = profile.ready()
    genuine = profile.run('trace', 'show', request_id, '--json').value['data']
    events = profile.audit()
    foreign = []
    for event in events:
        if event.get('request_id') == request_id and event['event'] in ('policy.decided', 'authz.decided'):
            assert event[field] != other
            copy = json.loads(json.dumps(event))
            copy[field] = other
            if copy['event'] == 'policy.decided':
                copy['decision']['decision_id'] = 'decision-' + '9' * 32
                copy['capability_id'] = WRITE
            else:
                copy['operation'] = 'forged_operation'
            foreign.append(copy)
    assert {event['event'] for event in foreign} == {'policy.decided', 'authz.decided'}
    profile.write_audit([*events, *foreign])
    for operation in ('show', 'explain'):
        run = profile.run('trace', operation, request_id, '--json')
        # Exactly the notes of the unedited record: none for show, the unrecorded catalog for explain.
        assert (run.code, run.value['uncertainties']) == (0, [] if operation == 'show' else [UNRANKED]), run.out
        assert 'forged_operation' not in run.out and '9' * 32 not in run.out and other not in run.out
    shown = profile.run('trace', 'show', request_id, '--json').value['data']
    assert shown['policy_decisions'] == genuine['policy_decisions'] and len(shown['policy_decisions']) == 1
    assert shown['authz_decisions'] == genuine['authz_decisions']


# ----------------------------------------------------------------- T03, T11: identifiers of another shape
@pytest.mark.parametrize('forged', ['not-a-request-id', 'request-' + 'A' * 32, 'request-' + '0' * 31, 'receipts',
                                    'request-' + '0' * 32 + ' and more text'])
def test_t03_t11_a_receipt_whose_request_id_has_another_shape_is_never_found(profile: Profile, forged: str) -> None:
    """M26-RT-02 in its S00 form: a lookup accepts only `request-<32 hex>` or a 32-hex trace id, and a
    receipt is the caller's record only when its own identifiers have that shape. A receipt edited to carry
    any other request id is not found by that id: the answer is byte-identical to the unknown-id answer.
    The two checks back each other; this test fails only when both are removed."""
    request_id = profile.ready()
    unknown = profile.run('trace', 'show', 'request-' + '0' * 32, '--json')
    assert unknown.summary == (4, 'DENIED', 'NOT_FOUND', 'trace_not_found')
    profile.rewrite_receipt(request_id, lambda record: record.update(request_id=forged))
    for operation in ('show', 'explain'):
        run = profile.run('trace', operation, '--json', '--', forged)
        assert (run.code, run.out) == (4, unknown.out), run.out
        assert profile.run('trace', operation, request_id, '--json').out == unknown.out     # the old id is gone too


# ----------------------------------------------------------------- P17, P10: a reader changes no mode
def test_p17_trace_show_changes_no_mode_and_refuses_a_permissive_receipts_directory(profile: Profile) -> None:
    """M01 "Data directory" rule 1: a reader modifies nothing. ``trace show`` leaves every file and
    directory mode as it found it, and a ``receipts`` directory with group or other bits is refused
    (``state_dir_unsafe``), never repaired by a read."""
    request_id = profile.ready()
    modes = profile.modes()
    assert set(modes.values()) == {0o700, 0o600}
    for operation in ('show', 'explain'):
        assert profile.run('trace', operation, request_id, '--json').code == 0
        assert profile.modes() == modes
    receipts = profile.data / 'receipts'
    receipts.chmod(0o755)
    for operation in ('show', 'explain'):
        assert_unsafe(profile.run('trace', operation, request_id, '--json'), 'receipts')
        assert stat.S_IMODE(receipts.stat().st_mode) == 0o755
    assert profile.modes() == {**modes, 'data/receipts': 0o755}
    receipts.chmod(0o700)
    assert profile.run('trace', 'show', request_id, '--json').code == 0


# ----------------------------------------------------------------- social: urgency alone, format characters
MARKERS_ALONE = ['urgent', 'URGENT!', 'urgently', 'urgente', 'This is urgent', 'It is urgent.', 'isto é urgente',
                 'isso é urgente', 'é urgente', 'urgent, this is urgent', 'urgente, é urgente']
FORMAT_CHARACTERS = ['he​llo', '​hello', 'hello​', 'hel‌lo', 'hel‍lo', 'hel­lo',
                     '⁠hello', 'hello⁠', '﻿hello', 'hello, ur​gent', 'bom​ dia',
                     'ol​á', 'good​morning', '‮hello', 'hello ​']
# Owner decision of 2026-11-16: the S00 social table supports English and Portuguese only. A greeting,
# pleasantry, thanks or urgency phrase of any other language is ordinary text: it goes to the model path.
OTHER_LANGUAGES = ['Hola', '¡Hola! ¿Qué tal?', 'Buenos días', 'gracias', 'Bonjour', 'Bonjour, ça va ?', 'Salut',
                   'merci', "Bonjour, c'est urgent", 'Hallo!', 'Guten Morgen', 'Wie geht es dir?', 'danke',
                   'das ist dringend, hallo', 'Hallo, es ist dringend', 'hello, dringend', 'Ciao, come stai?',
                   'Buongiorno', 'grazie', 'Goedemorgen', 'Merhaba!', 'Привет, как дела?', 'こんにちは', '你好',
                   '안녕하세요', 'नमस्ते', 'Namaste', 'مرحبا']
# The marker set is closed: a politeness, time or assent word next to a greeting carries a request.
OTHER_WORDS = ['hello, please', 'please, hello', 'olá, por favor', 'hello, now', 'hello, ok', 'thanks, go ahead',
               'bom dia, agora', 'hello, this', 'olá, isto']
SUPPORTED = [('Hello!', 'Hello!'), ('Hi, how are you? This is urgent.', 'Hello!'), ('thanks', 'Hello!'),
             ('Olá, tudo bem?', 'Olá!'), ('Bom dia', 'Olá!'), ('obrigado', 'Olá!'), ('Olá, isto é urgente', 'Olá!')]


@pytest.mark.parametrize('texts', [MARKERS_ALONE, FORMAT_CHARACTERS, OTHER_LANGUAGES, OTHER_WORDS],
                         ids=['urgency_alone', 'format_characters', 'other_languages', 'other_words'])
def test_text_outside_the_social_table_is_never_a_greeting(profile: Profile, texts: list) -> None:
    """SOC-01 negative and contract rule 2. With no provider every such text is the work refusal
    NOT_CONFIGURED (exit 3); with a probed scripted model that labels it ``social`` it is BLOCKED /
    NO_VERIFIED_EXECUTION (exit 4, decision D2). One-shot ``ask`` and ``chat --jsonl`` agree.

    Kills: markers alone are social (S06), a format character is dropped inside or around a word (S05c),
    any table entry, urgency phrase or marker of a language other than English and Portuguese, and a word
    added to the marker set (S17, "please")."""
    profile.ready()
    plain = profile.chat(texts)
    assert plain.code == 0 and 'GREETING' not in plain.out
    for text, turn in zip(texts, plain.values):
        assert summary(turn) == (None, *NOT_CONFIGURED[1:]), ascii(text)
        assert turn['data']['result_kind'] == 'BLOCKED' and 'text' not in turn['data']
    labelled = profile.chat(texts, LABELLED_SOCIAL * len(texts))
    assert labelled.code == 0 and CLAIM not in labelled.out and 'GREETING' not in labelled.out
    assert labelled.kinds('handler') == [] and labelled.kinds('script_left') == [['script_left', 0]]
    assert len(labelled.kinds('request')) == 3 * len(texts)            # every text reached the model
    for text, turn in zip(texts, labelled.values):
        assert summary(turn) == (None, *ANSWER_BLOCKED[1:]), ascii(text)
        assert (turn['data']['result_kind'], turn['data']['provider_used']) == ('BLOCKED', True)
    for text in (texts[0], texts[-1]):
        run = profile.run('ask', '--json', '--', text)
        assert run.summary == NOT_CONFIGURED, ascii(text)
        run = profile.scripted('ask', '--json', '--', text, script=LABELLED_SOCIAL)
        assert run.summary == ANSWER_BLOCKED and len(run.kinds('request')) == 3, ascii(text)


def test_english_and_portuguese_are_answered_by_the_table_with_no_model_call(profile: Profile) -> None:
    """The positive control of the test above: the two supported languages, in every provider state used there."""
    profile.ready()
    texts = [text for text, _reply in SUPPORTED]
    for run, script in ((profile.chat(texts), None), (profile.chat(texts, READ_SCRIPT), READ_SCRIPT)):
        assert run.code == 0
        for (text, reply), turn in zip(SUPPORTED, run.values):
            assert (turn['status'], turn['data']['result_kind'], turn['data']['text']) == ('SUCCEEDED', 'GREETING', reply), text
            assert turn['data']['provider_used'] is False
        if script is not None:
            no_model_or_handler(run, script)


# ----------------------------------------------------------------- P11: a data directory below a symbolic link
def test_p11_a_data_directory_below_a_symbolic_link_is_refused_by_every_command(profile: Profile) -> None:
    """M01 "Data directory" rule 1: no component of the path to the data directory is a symbolic link.
    The data directory itself is a real private directory here; only an ANCESTOR is a link."""
    request_id = profile.ready()
    link = profile.root / 'link'
    link.symlink_to(profile.root, target_is_directory=True)
    through = {'QUATI_DATA_DIR': str(link / 'data')}
    before, receipts = profile.tree(profile.data), len(list((profile.data / 'receipts').iterdir()))
    for argv in (LIST, ('capabilities', 'install-fixture', 'mail-search', '--enable-fixture', '--json'),
                 ('ask', 'hello', '--json'), ('trace', 'show', request_id, '--json')):
        assert_unsafe(profile.run(*argv, env=through), 'data_dir')
    for argv, script in ((('ask', WORK_TEXT, '--json'), READ_SCRIPT), (('models', 'probe', '--json'), [])):
        run = profile.scripted(*argv, script=script, env=through)
        assert_unsafe(run, 'data_dir')
        no_model_or_handler(run, script)
        assert run.kinds('probe_call') == []
    assert profile.tree(profile.data) == before and len(list((profile.data / 'receipts').iterdir())) == receipts
    assert profile.run(*LIST).code == 0                                 # the same directory by its real path

    (profile.root / 'fresh-root').mkdir()
    fresh = Profile(profile.root / 'fresh-root')                        # nothing initialized: init refuses first
    (fresh.root / 'real').mkdir()
    (fresh.root / 'link').symlink_to(fresh.root / 'real', target_is_directory=True)
    run = fresh.run('init', '--json', env={'QUATI_DATA_DIR': str(fresh.root / 'link' / 'data')})
    assert_unsafe(run, 'data_dir')
    assert list((fresh.root / 'real').iterdir()) == [] and not fresh.config.exists()


# ----------------------------------------------------------------- P19, P20: the measured report
def test_p19_the_measured_report_is_not_stored_through_a_directory_swapped_during_the_probe(profile: Profile) -> None:
    """The probe verifies its storage before it spends the provider call (M17 probe order), and the store
    verifies the directory chain again when it writes. ``feature_reports`` is replaced by a symbolic link
    while the provider is being called: the pointer is not written through the link, the answer says the
    report was not stored, and ``ask`` keeps refusing."""
    assert profile.run('init', '--json').code == 0
    assert profile.run('capabilities', 'install-fixture', 'calendar-read', '--enable-fixture', '--json').code == 0
    directory, moved = profile.data / 'feature_reports', profile.outside / 'moved-feature-reports'
    run = profile.scripted('models', 'probe', '--json', during_probe=[str(directory), str(moved)])
    value = run.value
    assert (run.code, value['status'], value['error']['code'], value['data']['reason']) == (
        4, 'UNAVAILABLE', 'TEMPORARILY_UNAVAILABLE', 'feature_report_not_stored'), (run.out, run.err)
    assert value['data']['stored'] == {'receipt': True, 'feature_report': False}
    assert value['data']['provider_call_made'] is True and len(run.kinds('probe_call')) == 1
    assert len(value['evidence_refs']) == 1 and 'internal error' not in run.err
    assert directory.is_symlink() and list(moved.iterdir()) == []       # nothing was written through the link
    asked = profile.scripted('ask', WORK_TEXT, '--json', script=READ_SCRIPT)
    assert_unsafe(asked, 'feature_reports')
    no_model_or_handler(asked, READ_SCRIPT)


def test_p20_a_symbolic_link_in_place_of_the_report_pointer_is_never_followed(profile: Profile) -> None:
    """A pointer that is not a private regular file measures nothing: the ask is refused as
    MODEL_INCOMPATIBLE before any model call, although the link leads to the genuine pointer bytes. A new
    probe replaces the link with a private file and the same ask then works."""
    profile.ready()
    pointers = list((profile.data / 'feature_reports').glob('*.json'))
    assert len(pointers) == 1
    moved = profile.outside / 'pointer.json'
    pointers[0].rename(moved)
    pointers[0].symlink_to(moved)
    genuine = moved.read_bytes()
    run = profile.scripted('ask', WORK_TEXT, '--json', script=READ_SCRIPT)
    assert run.summary == (4, 'UNAVAILABLE', 'UNSUPPORTED', 'MODEL_INCOMPATIBLE'), run.out
    no_model_or_handler(run, READ_SCRIPT)
    doctor = profile.scripted('doctor', '--json').value['data']['provider']
    assert doctor['measured_support'] != 'SUPPORTED' and doctor['status'] != 'PROBED'
    assert moved.read_bytes() == genuine
    assert profile.scripted('models', 'probe', '--json').code == 0
    assert not pointers[0].is_symlink() and stat.S_IMODE(pointers[0].stat().st_mode) == 0o600
    assert moved.read_bytes() == genuine
    assert profile.scripted('ask', WORK_TEXT, '--json', script=READ_SCRIPT).code == 0


# ----------------------------------------------------------------- X06, X07: the exit rule on the model path
def test_x06_an_audit_log_that_becomes_unsafe_during_the_turn_is_a_local_store_refusal_with_exit_4(profile: Profile) -> None:
    """M01 exit table rows 4 and 5: a failure of the local audit log is never a provider failure, also when
    it appears after the ask was admitted. The log is replaced by a symbolic link while the model is being
    asked for the first time; the next tool call cannot be logged, so nothing executes, nothing is written
    through the link, and the ask ends `audit_unavailable` with exit 4 (not 5)."""
    profile.ready()
    moved = profile.outside / 'moved-audit.jsonl'
    run = profile.scripted('ask', WORK_TEXT, '--json', script=READ_SCRIPT,
                           during_first_model_request=[str(profile.audit_path), str(moved)])
    value = run.value
    assert (run.code, value['error']['code'], value['data']['reason']) == (
        4, 'TEMPORARILY_UNAVAILABLE', 'audit_unavailable'), (run.out, run.err)
    assert value['status'] == 'UNAVAILABLE' and value['data']['launched'] is False
    assert run.kinds('handler') == [] and len(run.kinds('request')) >= 1
    assert not any(step['handler_executed'] for step in value['data']['tool_calls'])
    admitted = [json.loads(line) for line in moved.read_bytes().splitlines()][-1]
    assert (admitted['event'], admitted['operation']) == ('authz.decided', 'ask_admission')   # the last line written
    assert profile.audit_path.is_symlink()


# ----------------------------------------------------------------- P32b: the probe order
@pytest.mark.parametrize('argv', [('models', 'probe', '--json'), ('doctor', '--probe', '--json')])
def test_p32b_an_unconfigured_probe_is_not_configured_before_any_authentication(profile: Profile, argv) -> None:
    """M17 probe order: configured, authenticate, storage, authorize, call. With no provider configured
    and no identity at all the answer is NOT_CONFIGURED (exit 3), never UNAUTHENTICATED (exit 4), and
    nothing is created."""
    run = profile.run(*argv)
    value = run.value
    assert (run.code, value['status'], value['error']['code']) == (3, 'BLOCKED', 'NOT_CONFIGURED'), run.out
    assert not profile.config.exists() and not profile.data.exists()
    assert profile.run('init', '--json').code == 0                      # the same answer with an identity
    again = profile.run(*argv).value
    assert (again['status'], again['error']['code'], again['uncertainties']) == (
        'BLOCKED', 'NOT_CONFIGURED', value['uncertainties'])


# ----------------------------------------------------------------- I02, I05, I08: the installation record
def assert_rejected_everywhere(profile: Profile, reason: str, detail: str) -> None:
    doctor = profile.run('doctor', '--json')
    identity = doctor.value['data']['identity']
    assert doctor.code == 0 and (identity['status'], identity['reason'], identity['detail']) == (
        'INVALID', reason, detail)
    for argv in (('ask', 'hello', '--json'), LIST):
        assert profile.run(*argv).summary == UNAUTHENTICATED


def test_i05_a_signed_record_of_another_os_user_is_rejected(profile: Profile) -> None:
    """RFC-013 section 4: the installation record names the OS user it was created for. A record that is
    correctly signed by the device key but carries another ``owner_uid`` authenticates nobody."""
    assert profile.run('init', '--json').code == 0
    assert json.loads((profile.config / 'identity.json').read_bytes())['owner_uid'] == os.getuid()
    for other in (os.getuid() + 1, 0 if os.getuid() else 1, str(os.getuid()), None):
        profile.resign(owner_uid=other)
        assert_rejected_everywhere(profile, 'credential_corrupt', 'record_rejected')
    profile.resign(owner_uid=os.getuid())                               # control: only the owner field decided
    assert profile.run('ask', 'hello', '--json').code == 0


@pytest.mark.parametrize('field', ['tenant_id', 'principal_id', 'personal_space_id', 'organization_space_id'])
def test_i02_a_signed_record_with_an_empty_identifier_is_rejected(profile: Profile, field: str) -> None:
    assert profile.run('init', '--json').code == 0
    profile.resign(**{field: ''})
    assert_rejected_everywhere(profile, 'credential_corrupt', 'record_field_missing')


def test_i08_no_credential_state_is_shown_inside_a_capability_context(profile: Profile) -> None:
    """M02: a process that runs as a capability (``QUATI_CAPABILITY_CONTEXT``) cannot use the local
    credential and is told nothing about it: the identity is NOT_CONFIGURED / ``credential_missing`` with
    no detail, whether the credential is intact or broken; every command is UNAUTHENTICATED."""
    assert profile.run('init', '--json').code == 0
    inside = {'QUATI_CAPABILITY_CONTEXT': '1'}
    expected = ('NOT_CONFIGURED', 'credential_missing', None)
    identity = profile.run('doctor', '--json', env=inside).value['data']['identity']
    assert (identity['status'], identity['reason'], identity['detail']) == expected
    (profile.config / 'identity.json').chmod(0o644)
    outside = profile.run('doctor', '--json').value['data']['identity']
    assert (outside['status'], outside['reason'], outside['detail']) == (
        'INVALID', 'credential_insecure', 'identity_file_mode')
    identity = profile.run('doctor', '--json', env=inside).value['data']['identity']
    assert (identity['status'], identity['reason'], identity['detail']) == expected
    (profile.config / 'identity.json').chmod(0o600)
    for argv in (('ask', 'hello', '--json'), LIST):
        assert profile.run(*argv, env=inside).summary == UNAUTHENTICATED
    assert profile.run('ask', 'hello', '--json').code == 0
