"""S00-T01 ``quati chat`` line-session contract (M01-FR-04, M01-AT-03, M01-RT-03).

Proof tier: L1 deterministic. The read-dispatch-print loop is driven in process through
``quati.cli.chat.run_chat`` with a scripted fake service (a call recorder; it is never a model
or provider) and through the public ``quati.cli.main.main`` entry with a real LOCAL identity in
a temporary directory. No network, live model, sleep or wall-clock assertion is used.

Line rules under test come from docs/prds/M01.md section "Chat session". Where M01 is silent
(NUL byte in a chat line) the conservative fail-closed rule implemented is: the line gets an
``INVALID_INPUT`` Response (``data.reason = "chat_nul_byte"``), no use case is called and the
session ends with exit 2. Reason tags live in ``data.reason`` because the Error schema is closed.
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import jsonschema
import pytest

import quati.cli.main as cli_main
from quati.adapters.local_identity import LocalIdentity
from quati.application.cli_service import response
from quati.application.identity import AccessDenied
from quati.cli.chat import MAX_LINE_BYTES, run_chat

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONTRACT = json.loads((REPOSITORY_ROOT / 'contracts' / 'runtime-boundaries.schema.json').read_text(encoding='utf-8'))
RESPONSE_SCHEMA = {'$schema': CONTRACT['$schema'], '$ref': '#/$defs/Response', '$defs': CONTRACT['$defs']}
SIX_KEYS = {'status', 'data', 'evidence_refs', 'uncertainties', 'next_action', 'error'}


class Recorder:
    """Scripted fake application service: records every use-case call; never a model."""

    def __init__(self, replies=None, raise_on=None):
        self.calls = []
        self.replies = replies or {}
        self.raise_on = raise_on or {}

    def ask(self, text):
        self.calls.append(('ask', text))
        if text in self.raise_on:
            raise self.raise_on[text]
        reply = self.replies.get(text, 'fake reply')
        return 0, response(data={'result_status': 'RESPONDED', 'text': reply})

    def unsupported(self, command):
        self.calls.append(('unsupported', command))
        return 4, response('UNAVAILABLE', None, 'UNSUPPORTED', f'fake {command} unsupported', 'fake next action')


def drive(raw: bytes, service=None, *, jsonl=True, interactive=False, stdin=None):
    service = service or Recorder()
    stdout, stderr = io.StringIO(), io.StringIO()
    code = run_chat(lambda: service, stdin or io.BytesIO(raw), stdout, stderr, jsonl=jsonl, interactive=interactive)
    lines = stdout.getvalue().splitlines()
    return code, [json.loads(line) for line in lines], service, stderr.getvalue(), stdout.getvalue()


def reason(value):
    assert value['status'] == 'DENIED' and value['error']['code'] == 'INVALID_INPUT'
    return value['data']['reason']


def test_fr04_jsonl_one_response_per_nonblank_line_through_one_shot_use_cases():
    """M01-FR-04 oracle: Hello, empty, /help, /status c-1, /bogus, /quit -> 5 Responses, exit 0."""
    code, values, service, stderr, raw = drive(b'Hello\n\n/help\n/status c-1\n/bogus\n/quit\nHello\n')
    assert code == 0
    assert len(raw.splitlines()) == 5 and raw.endswith('\n')
    for value in values:
        assert set(value) == SIX_KEYS
        jsonschema.validate(value, RESPONSE_SCHEMA)
    assert service.calls == [('ask', 'Hello'), ('unsupported', 'status')]
    assert values[1]['status'] == 'SUCCEEDED' and values[1]['data']['commands']
    assert values[2]['error']['code'] == 'UNSUPPORTED'
    assert reason(values[3]) == 'chat_unknown_command'
    assert values[4] == response(data={'result_kind': 'SESSION_ENDED'})
    assert stderr == ''


def test_fr04_end_of_input_without_quit_exits_zero_and_failed_turns_do_not_stop_the_loop():
    service = Recorder()
    service.ask = lambda text: (service.calls.append(('ask', text)) or
                                (3, response('BLOCKED', {}, 'NOT_CONFIGURED', 'fake', 'fake next')))
    code, values, _, _, _ = drive(b'work one\n/bogus\nwork two', service)
    assert code == 0
    assert [v['status'] for v in values] == ['BLOCKED', 'DENIED', 'BLOCKED']
    assert service.calls == [('ask', 'work one'), ('ask', 'work two')]


def test_fr04_each_response_is_written_and_flushed_before_the_next_line_is_read():
    class FlushVisible:
        """Only flushed text counts as written."""

        def __init__(self):
            self.pending, self.flushed = '', ''

        def write(self, text):
            self.pending += text
            return len(text)

        def flush(self):
            self.flushed, self.pending = self.flushed + self.pending, ''

    stdout = FlushVisible()

    class CheckingInput:
        def __init__(self, lines):
            self.lines, self.nonblank, self.reads = list(lines), 0, 0

        def readline(self, limit):
            assert len(stdout.flushed.splitlines()) == self.nonblank
            self.reads += 1
            line = self.lines.pop(0) if self.lines else b''
            self.nonblank += bool(line.strip())
            return line

    source = CheckingInput([b'one\n', b'\n', b'two\n'])
    assert run_chat(lambda: Recorder(), source, stdout, io.StringIO(), jsonl=True, interactive=False) == 0
    assert len(stdout.flushed.splitlines()) == 2 and stdout.pending == '' and source.reads == 4


def test_fr04_help_lists_exactly_the_m01_chat_table():
    code, values, service, _, _ = drive(b'/help\n')
    assert code == 0 and service.calls == []
    words = [row['input'] for row in values[0]['data']['commands']]
    assert words == ['', 'TEXT', '/status COMMITMENT_ID', '/tell COMMITMENT_ID TEXT', '/approvals [STATE]',
                     '/approve APPROVAL_REQUEST_ID', '/deny APPROVAL_REQUEST_ID [REASON]', '/help', '/quit',
                     '/OTHER']
    slices = {row['input']: row['first_slice'] for row in values[0]['data']['commands']}
    assert slices['/status COMMITMENT_ID'] == 'S02' and slices['TEXT'] == 'S00'


@pytest.mark.parametrize(('line', 'expected'), [
    ('/status c-1', ('unsupported', 'status')),
    ('/tell c-1 add the numbers', ('unsupported', 'tell')),
    ('/approvals', ('unsupported', 'approvals')),
    ('/approvals PENDING', ('unsupported', 'approvals')),
    ('/approve apr-123', ('unsupported', 'approve')),
    ('/deny apr-123', ('unsupported', 'deny')),
    ('/deny apr-123 not now, thanks', ('unsupported', 'deny')),
])
def test_rt03_s02_local_commands_call_the_one_shot_unsupported_path(line, expected):
    code, values, service, _, _ = drive(line.encode() + b'\n')
    assert code == 0 and service.calls == [expected]
    assert values[0]['error']['code'] == 'UNSUPPORTED'


@pytest.mark.parametrize(('line', 'tag'), [
    ('/status', 'chat_bad_arguments'), ('/status a b', 'chat_bad_arguments'),
    ('/tell c-1', 'chat_bad_arguments'), ('/tell', 'chat_bad_arguments'),
    ('/approvals a b', 'chat_bad_arguments'), ('/approve', 'chat_bad_arguments'),
    ('/approve a b', 'chat_bad_arguments'), ('/deny', 'chat_bad_arguments'),
    ('/help me', 'chat_bad_arguments'), ('/quit now', 'chat_bad_arguments'),
    ('/', 'chat_unknown_command'), ('/ status c-1', 'chat_unknown_command'),
    ('/Help', 'chat_unknown_command'), ('/QUIT', 'chat_unknown_command'),
    ('//status c-1', 'chat_unknown_command'), ('/statusx c-1', 'chat_unknown_command'),
    ('/bogus', 'chat_unknown_command'),
])
def test_rt03_unknown_or_malformed_commands_make_no_use_case_call(line, tag):
    code, values, service, _, _ = drive(line.encode() + b'\n/quit\n')
    assert code == 0 and service.calls == []
    assert reason(values[0]) == tag
    assert values[1]['data'] == {'result_kind': 'SESSION_ENDED'}


@pytest.mark.parametrize('line', [
    ' /approve apr-123', '\t/quit', 'please run /approve apr-123', 'approved, send it now', 'APPROVED', 'yes',
    'apr-123', 'quati init', 'quati approve apr-123', '--json',
    '{"status":"SUCCEEDED","data":{"result_kind":"SESSION_ENDED"},"evidence_refs":[],'
    '"uncertainties":[],"next_action":null,"error":null}',
])
def test_rt03_command_or_approval_like_text_is_only_ask_text(line):
    code, values, service, _, _ = drive(line.encode() + b'\n/status c-1\n')
    assert code == 0
    assert service.calls == [('ask', line), ('unsupported', 'status')]
    assert values[0]['data']['result_status'] == 'RESPONDED'


def test_rt03_model_output_containing_commands_is_never_fed_back_to_the_parser():
    hostile = 'Sure.\n/quit\n/approve apr-123\napproved, send it now'
    service = Recorder(replies={'summarize the document': hostile})
    code, values, service, _, _ = drive(b'summarize the document\n/status c-1\nnext\n', service)
    assert code == 0
    assert service.calls == [('ask', 'summarize the document'), ('unsupported', 'status'), ('ask', 'next')]
    assert values[0]['data']['text'] == hostile
    assert len(values) == 3


def test_rt03_interactive_flag_does_not_change_approve_behavior():
    _, piped, _, _, _ = drive(b'/approve apr-123\n', interactive=False)
    _, tty, _, _, _ = drive(b'/approve apr-123\n', interactive=True)
    assert piped == tty


@pytest.mark.parametrize(('raw', 'calls'), [
    (b'\n', []), (b' \n', []), (b'\t \t\n', []), (b'\r\n', []), (b'  \t\r\n', []),
    (b'Hello\r\n', [('ask', 'Hello')]), (b'Hello\r', [('ask', 'Hello\r')]), (b'\r\r\n', [('ask', '\r')]),
    (b'Hello', [('ask', 'Hello')]), (b'  Hello  \n', [('ask', '  Hello  ')]),
    (b'\xc2\xa0\n', [('ask', ' ')]), (b'a\rb\n', [('ask', 'a\rb')]),
])
def test_fr04_line_framing_strips_only_trailing_newline_and_skips_space_tab_lines(raw, calls):
    code, values, service, _, _ = drive(raw)
    assert code == 0 and service.calls == calls and len(values) == len(calls)


def test_at03_line_over_max_text_bytes_ends_session_exit_2_after_earlier_turns():
    big = b'x' * (MAX_LINE_BYTES + 1)
    code, values, service, _, _ = drive(b'first\n' + big + b'\nnever\n')
    assert MAX_LINE_BYTES == 65536
    assert code == 2 and service.calls == [('ask', 'first')]
    assert reason(values[1]) == 'chat_line_too_long' and len(values) == 2


@pytest.mark.parametrize('raw', [b'x' * MAX_LINE_BYTES + b'\n', b'x' * MAX_LINE_BYTES + b'\r\n',
                                 b'x' * MAX_LINE_BYTES, 'é'.encode() * (MAX_LINE_BYTES // 2) + b'\n'])
def test_at03_line_of_exactly_max_text_bytes_is_a_turn(raw):
    code, values, service, _, _ = drive(raw + b'/quit\n' if raw.endswith(b'\n') else raw)
    assert code == 0 and len(service.calls) == 1
    assert len(service.calls[0][1].encode()) == MAX_LINE_BYTES


@pytest.mark.parametrize('raw', [b'x' * (MAX_LINE_BYTES + 1), b'x' * (MAX_LINE_BYTES + 1) + b'\r\n',
                                 b'x' * (MAX_LINE_BYTES * 3) + b'\n'])
def test_at03_over_limit_variants_are_rejected_without_a_call(raw):
    code, values, service, _, _ = drive(raw + b'/quit\n')
    assert code == 2 and service.calls == [] and len(values) == 1
    assert reason(values[0]) == 'chat_line_too_long'


@pytest.mark.parametrize(('raw', 'tag'), [
    (b'\xff\n', 'chat_invalid_utf8'), (b'caf\xe9\n', 'chat_invalid_utf8'),
    (b'\xed\xa0\x80\n', 'chat_invalid_utf8'), (b'\xc0\xaf\n', 'chat_invalid_utf8'),
    (b'a\x00b\n', 'chat_nul_byte'), (b'/status c\x001\n', 'chat_nul_byte'), (b'\x00\n', 'chat_nul_byte'),
])
def test_at03_untrustworthy_framing_ends_session_exit_2_without_a_call(raw, tag):
    code, values, service, _, _ = drive(b'ok\n' + raw + b'after\n')
    assert code == 2 and service.calls == [('ask', 'ok')]
    assert len(values) == 2 and reason(values[1]) == tag
    jsonschema.validate(values[1], RESPONSE_SCHEMA)


def test_fr04_authentication_failure_in_a_turn_ends_session_exit_4():
    service = Recorder(raise_on={'second': AccessDenied()})
    code, values, service, _, _ = drive(b'first\nsecond\nthird\n', service)
    assert code == 4 and service.calls == [('ask', 'first'), ('ask', 'second')]
    assert values[1]['status'] == 'DENIED' and values[1]['error']['code'] == 'UNAUTHENTICATED'


@pytest.mark.parametrize('error', [OSError('disk detail'), ValueError('bad detail'), RuntimeError('secret-detail')])
def test_fr04_internal_error_in_a_turn_ends_session_exit_1_sanitized(error):
    service = Recorder(raise_on={'second': error})
    code, values, service, stderr, raw = drive(b'first\nsecond\nthird\n', service)
    assert code == 1 and len(values) == 2
    assert values[1]['status'] == 'BLOCKED' and values[1]['error']['code'] == 'INTERNAL_ERROR'
    assert 'detail' not in raw + stderr
    assert stderr.strip() == f'quati: internal error ({type(error).__name__}); no work was accepted.'


def test_fr04_sigint_at_prompt_or_during_turn_exits_130_without_output():
    class Interrupting:
        def readline(self, limit):
            raise KeyboardInterrupt

    code, values, service, _, raw = drive(b'', stdin=Interrupting())
    assert code == 130 and raw == '' and service.calls == []
    service = Recorder(raise_on={'work': KeyboardInterrupt()})
    code, values, service, _, raw = drive(b'work\nmore\n', service)
    assert code == 130 and raw == '' and service.calls == [('ask', 'work')]


def test_fr04_prompt_goes_to_stderr_only_for_interactive_human_mode():
    code, human_tty, _, stderr, raw = drive(b'Hello\n\n/quit\n', jsonl=False, interactive=True)
    assert code == 0 and stderr == 'quati> ' * 3
    _, jsonl_values, _, jsonl_err, jsonl_raw = drive(b'Hello\n\n/quit\n', jsonl=True, interactive=True)
    _, piped, _, piped_err, _ = drive(b'Hello\n\n/quit\n', jsonl=False, interactive=False)
    assert jsonl_err == '' and piped_err == ''
    # One-shot commands currently print the JSON envelope with or without --json, so the human
    # rendering of a chat turn equals the --jsonl line.
    assert raw == jsonl_raw and human_tty == jsonl_values == piped


@pytest.fixture
def local_profile(tmp_path, monkeypatch):
    for name in ('QUATI_BASE_URL', 'QUATI_MODEL', 'QUATI_ALLOW_LIVE', 'QUATI_API_KEY_ENV', 'QUATI_API_KEY',
                 'QUATI_PROVIDER', 'QUATI_CAPABILITY_CONTEXT'):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('QUATI_CONFIG_DIR', str(tmp_path / 'config'))
    monkeypatch.setenv('QUATI_DATA_DIR', str(tmp_path / 'data'))
    return tmp_path


class FakeStdin:
    def __init__(self, raw, tty=False):
        self.buffer, self.tty = io.BytesIO(raw), tty

    def isatty(self):
        return self.tty


def run_main(monkeypatch, capsys, argv, raw=b'', tty=False):
    monkeypatch.setattr('sys.stdin', FakeStdin(raw, tty))
    code = cli_main.main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_at03_in_process_chat_equals_one_shot_for_real_local_identity(local_profile, monkeypatch, capsys):
    LocalIdentity(local_profile / 'config').initialize()
    code, out, err = run_main(monkeypatch, capsys, ['chat', '--jsonl'],
                              b'Hello.\nHello, please summarize tomorrow\'s calendar.\n/approve apr-123\n/quit\n')
    assert code == 0 and err == ''
    chat = [json.loads(line) for line in out.splitlines()]
    one_shot = []
    for argv in (['ask', '--json', '--', 'Hello.'],
                 ['ask', '--json', '--', 'Hello, please summarize tomorrow\'s calendar.'],
                 ['approve', 'apr-123', '--json']):
        exit_code, text, _ = run_main(monkeypatch, capsys, argv)
        one_shot.append((exit_code, json.loads(text)))
    assert [e for e, _ in one_shot] == [0, 3, 4]
    conversation_id = chat[0]['data']['conversation']['id']
    for index, (got, (_, expected)) in enumerate(zip(chat[:3], one_shot), 1):
        if got['data'] and 'request_id' in got['data']:
            metadata = got['data'].pop('conversation')
            assert metadata == dict(id=conversation_id, revision=index, lifetime='PROCESS_ONLY',
                                    continues_after_exit=False)
            assert 'conversation' not in expected['data']
        for value in (got, expected):
            if value['data'] and 'request_id' in value['data']:
                value['data'].update(request_id='<id>', trace_id='<id>')
                value['evidence_refs'] = ['<ref>' for _ in value['evidence_refs']]
        assert got == expected
    assert chat[3]['data'] == {'result_kind': 'SESSION_ENDED'}
    assert len(list((local_profile / 'data' / 'receipts').iterdir())) == 4


def test_fr04_chat_through_main_with_tty_prompts_and_pre_init_ask_exits_4(local_profile, monkeypatch, capsys):
    code, out, err = run_main(monkeypatch, capsys, ['chat'], b'/help\nHello\n/quit\n', tty=True)
    assert code == 4
    values = [json.loads(line) for line in out.splitlines()]
    assert values[0]['status'] == 'SUCCEEDED'
    assert (values[1]['status'], values[1]['error']['code']) == ('DENIED', 'UNAUTHENTICATED')
    assert len(values) == 2 and err == 'quati> ' * 2


@pytest.mark.parametrize('argv', [
    ['status', 'c-1', '--json'], ['tell', 'c-1', 'more text', '--json'], ['approvals', 'list', '--json'],
    ['approvals', 'list', '--state', 'PENDING', '--json'], ['approve', 'apr-123', '--json'],
    ['deny', 'apr-123', '--json'], ['deny', 'apr-123', '--reason', 'not now', '--json'],
])
def test_fr01_not_yet_delivered_one_shot_commands_return_unsupported_exit_4(local_profile, monkeypatch, capsys, argv):
    code, out, err = run_main(monkeypatch, capsys, argv)
    value = json.loads(out)
    assert code == 4 and err == ''
    jsonschema.validate(value, RESPONSE_SCHEMA)
    assert value['status'] == 'UNAVAILABLE' and value['error']['code'] == 'UNSUPPORTED'
    assert not (local_profile / 'data').exists() and not (local_profile / 'config').exists()


def test_fr04_chat_rejects_extra_arguments_as_invalid_input(local_profile, monkeypatch, capsys):
    code, out, _ = run_main(monkeypatch, capsys, ['chat', 'Hello', '--jsonl'])
    assert code == 2 and json.loads(out)['error']['code'] == 'INVALID_INPUT'


# --- Audit fixes (2026-11-16) ------------------------------------------------------------------

def quati_json(value) -> str:
    """Independent quati-json/1 oracle (BOUNDARY_CONTRACTS.md, Canonical digest; M01 cli.json_indent)."""
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def test_fr04_jsonl_lines_are_exactly_quati_json_1():
    service = Recorder(replies={'olá': '¡Olá, ação! 😀'})
    _, values, _, _, raw = drive('olá\n/help\n/bogus\n/status c-1\n/quit\n'.encode(), service)
    assert raw == ''.join(quati_json(value) + '\n' for value in values)
    assert raw.isascii() and '\\u00a1Ol\\u00e1' in raw and '\\ud83d\\ude00' in raw


@pytest.mark.parametrize('argv', [['doctor', '--json'], ['status', 'c-1', '--json'], ['ask', '--json', '--', 'olá!'],
                                  ['ask', '--json', '--', ''], ['does-not-exist']])
def test_fr01_one_shot_json_output_is_exactly_quati_json_1(local_profile, monkeypatch, capsys, argv):
    LocalIdentity(local_profile / 'config').initialize()
    _, out, _ = run_main(monkeypatch, capsys, argv)
    assert out == quati_json(json.loads(out)) + '\n'


def write_policy(config: Path, tenant_id: str, mode=0o600, raw=None, description=None):
    """Replace any policy file (hand edit); ``description`` alters the document so its version changes."""
    document = json.loads((REPOSITORY_ROOT / 'examples' / 'policies' / 'local-default.policy.json').read_text())
    if description is not None:
        document['description'] = description
    path = config / 'policy.json'
    path.unlink(missing_ok=True)
    path.write_bytes(raw if raw is not None else json.dumps({**document, 'tenant_id': tenant_id}).encode())
    path.chmod(mode)
    return path


def doctor_policy(monkeypatch, capsys):
    code, out, _ = run_main(monkeypatch, capsys, ['doctor', '--json'])
    assert code == 0
    value = json.loads(out)
    jsonschema.validate(value, RESPONSE_SCHEMA)
    return value['data']['policy'], out


@pytest.mark.parametrize(('leg', 'reason'), [
    ('absent', 'missing'), ('invalid_json', 'parse_error'), ('schema_invalid', 'schema_invalid'),
    ('wrong_tenant', 'wrong_tenant'), ('mode_0644', 'wrong_mode'), ('symlink', 'not_regular_file'),
    ('valid_out_of_band', 'out_of_band_change'),
])
def test_m25_rt01_doctor_names_the_policy_unavailable_cause(local_profile, monkeypatch, capsys, leg, reason):
    """M25-RT-01 (doctor leg): the cause code is reported; no policy content is echoed."""
    code, out, _ = run_main(monkeypatch, capsys, ['init', '--json'])
    assert code == 0
    config = local_profile / 'config'
    tenant = json.loads(out)['data']['tenant_id']
    if leg == 'absent':
        (config / 'policy.json').unlink()
    elif leg == 'invalid_json':
        write_policy(config, tenant, raw=b'{"tenant_id": "' + tenant.encode() + b'", "secret-marker"')
    elif leg == 'schema_invalid':
        write_policy(config, tenant, raw=json.dumps({'tenant_id': tenant, 'note': 'secret-marker'}).encode())
    elif leg == 'wrong_tenant':
        write_policy(config, '01JD0000000000000000000002')
    elif leg == 'mode_0644':
        write_policy(config, tenant, mode=0o644)
    elif leg == 'symlink':
        target = write_policy(local_profile, tenant)
        (config / 'policy.json').unlink()
        (config / 'policy.json').symlink_to(target)
    elif leg == 'valid_out_of_band':
        write_policy(config, tenant, description='Hand edited outside quati policy apply.')
    policy, out = doctor_policy(monkeypatch, capsys)
    assert policy == {'status': 'UNAVAILABLE', 'reason': reason}
    assert 'secret-marker' not in out and 'read-own-spaces' not in out


def test_m25_rt01_doctor_policy_before_init_and_loader_raising(local_profile, monkeypatch, capsys):
    policy, _ = doctor_policy(monkeypatch, capsys)
    assert policy == {'status': 'UNAVAILABLE', 'reason': 'missing'}
    (local_profile / 'config').mkdir(mode=0o700)
    write_policy(local_profile / 'config', '01JD0000000000000000000000')
    policy, _ = doctor_policy(monkeypatch, capsys)
    assert policy == {'status': 'UNAVAILABLE', 'reason': 'identity_unavailable'}

    def explode(*args, **kwargs):
        raise RuntimeError('secret-marker')

    LocalIdentity(local_profile / 'config.d').initialize()
    monkeypatch.setenv('QUATI_CONFIG_DIR', str(local_profile / 'config.d'))
    monkeypatch.setattr('quati.cli.local_policy.load_trusted_policy', explode)
    policy, out = doctor_policy(monkeypatch, capsys)
    assert policy == {'status': 'UNAVAILABLE', 'reason': 'loader_error'} and 'secret-marker' not in out


def test_m25_rt01_doctor_reports_available_only_for_a_trusted_policy(tmp_path):
    from quati.application.cli_service import CLIService
    from quati.application.ports import ProviderConfig
    from quati.domain.policy import PolicyState

    identity = LocalIdentity(tmp_path / 'config')
    tenant = identity.initialize()['tenant_id']
    seen = []
    trusted = PolicyState(True, None, tenant)
    service = CLIService(identity, ProviderConfig(), lambda record: {}, policy_loader=lambda t: seen.append(t) or trusted)
    assert service.doctor()[1]['data']['policy'] == {'status': 'AVAILABLE', 'reason': None}
    assert seen == [tenant]
    default = CLIService(identity, ProviderConfig(), lambda record: {})
    assert default.doctor()[1]['data']['policy'] == {'status': 'UNAVAILABLE', 'reason': 'loader_error'}


# --- RFC-014 5.1 init policy installation: edge branches (public paths in tests/integration/cli/test_init_policy.py)

def test_init_reports_template_problems_and_writes_no_policy(local_profile, monkeypatch, capsys, tmp_path):
    import quati.cli.local_policy as local_policy

    monkeypatch.setattr(local_policy, 'TEMPLATE', tmp_path / 'absent.policy.json')
    code, out, _ = run_main(monkeypatch, capsys, ['init', '--json'])
    value = json.loads(out)
    assert code == 0 and value['data']['policy'] == {'action': 'NOT_INSTALLED', 'reason': 'template_missing'}
    assert value['evidence_refs'] == []
    assert not (local_profile / 'config' / 'policy.json').exists()
    assert not (local_profile / 'config' / 'policy.registry.json').exists()
    bad = tmp_path / 'bad.policy.json'
    bad.write_text('{"tenant_id": "x"}')
    monkeypatch.setattr(local_policy, 'TEMPLATE', bad)
    code, out, _ = run_main(monkeypatch, capsys, ['init', '--json'])
    assert json.loads(out)['data']['policy'] == {'action': 'NOT_INSTALLED', 'reason': 'schema_invalid'}
    # Only the identity files and the empty flock sibling (quati.behavior.fsutil.locked) exist.
    assert sorted(p.name for p in (local_profile / 'config').iterdir()) == ['device.key', 'identity.json',
                                                                           'policy.json.lock']
    assert (local_profile / 'config' / 'policy.json.lock').read_bytes() == b''


def test_initialize_without_policy_installer_keeps_identity_summary(tmp_path):
    from quati.application.cli_service import CLIService
    from quati.application.ports import ProviderConfig

    service = CLIService(LocalIdentity(tmp_path / 'config'), ProviderConfig(), lambda record: {})
    code, value = service.initialize()
    assert code == 0 and 'policy' not in value['data'] and value['evidence_refs'] == []


def test_init_in_process_installs_once_then_never_replaces(local_profile, monkeypatch, capsys):
    config = local_profile / 'config'
    code, out, _ = run_main(monkeypatch, capsys, ['init', '--json'])
    assert code == 0 and json.loads(out)['data']['policy']['action'] == 'INSTALLED'
    assert doctor_policy(monkeypatch, capsys)[0] == {'status': 'AVAILABLE', 'reason': None}
    before = {path.name: path.read_bytes() for path in config.iterdir()}
    _, out, _ = run_main(monkeypatch, capsys, ['init', '--json'])
    assert json.loads(out)['data']['policy'] == {'action': 'UNCHANGED', 'reason': 'policy_exists'}
    (config / 'policy.json').unlink()
    _, out, _ = run_main(monkeypatch, capsys, ['init', '--json'])
    assert json.loads(out)['data']['policy'] == {'action': 'UNCHANGED', 'reason': 'registry_exists'}
    before.pop('policy.json')
    assert {path.name: path.read_bytes() for path in config.iterdir()} == before
