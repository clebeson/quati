"""S00-T01-A04 / M01-AT-03: ``quati chat --jsonl`` equals the one-shot command sequence.

Location follows the M01 test oracle (tests/integration/cli/test_chat_session.py). The
WORK_PACKAGES planned path tests/integration/test_s00_t01.py::test_a04 cannot be used: its
basename collides with tests/unit/test_s00_t01.py under pytest rootdir import mode.

Proof tier: L1 public process. Every run is an actual ``python -m quati`` subprocess with a
non-TTY stdin pipe, a real LOCAL identity and real receipt files in temporary directories.
No provider is configured, every ``QUATI_*`` variable is removed (``QUATI_ALLOW_LIVE`` is never
set) and no network or model is reached.

Identical seeding: one ``quati init`` profile is created and copied byte-for-byte (modes kept)
into profile A (chat) and profile B (one-shot), so both share one principal.

Normalization (the only fields allowed to differ between A and B; everything else must be
byte-equal canonical JSON):

* ``data.request_id`` (``request-`` + 32 hex) and ``data.trace_id`` (32 hex): fresh per call by
  RFC-013/M02, replaced by ``<request_id>``/``<trace_id>`` after the pattern is checked.
* each ``evidence_refs`` item ``sha256:<64 hex>:<path>``: the path must be a receipt in that
  profile's own ``receipts`` directory and the digest must equal the file bytes; it is then
  replaced by ``<receipt>``. The digest differs because the receipt holds the ids and time.
* receipt fields ``request_id``, ``trace_id`` (must equal the printed ones), ``timestamp`` and
  ``output_hash`` (must equal sha256 of the canonical printed Response with empty
  ``evidence_refs``, i.e. the object the use case hashed) are removed before comparison.

Receipts are ordered by the turn whose Response references them. The rest of each profile
tree (relative paths and bytes) must be identical, and the seeded config must be unchanged.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest

from quati.application.identity import canonical_bytes

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
TRANSCRIPT = Path(__file__).resolve().parent / 'fixtures' / 'chat_transcript_s00.txt'
# Golden mapping from M01 "Chat session": transcript line -> equivalent one-shot argv, or a
# literal expectation for session-local lines; None means "no turn, no output".
EQUIVALENTS = [
    ('Hello', ['ask', '--json', '--', 'Hello']),
    ('', None),
    (' \t', None),
    ('olá!', ['ask', '--json', '--', 'olá!']),
    ("Hello, please summarize tomorrow's calendar.",
     ['ask', '--json', '--', "Hello, please summarize tomorrow's calendar."]),
    ('/help', 'HELP'),
    ('/status c-1', ['status', 'c-1', '--json']),
    ('/tell c-1 add the budget numbers', ['tell', 'c-1', 'add the budget numbers', '--json']),
    ('/approvals PENDING', ['approvals', 'list', '--state', 'PENDING', '--json']),
    ('/approve apr-123', ['approve', 'apr-123', '--json']),
    ('/deny apr-123 not now', ['deny', 'apr-123', '--reason', 'not now', '--json']),
    ('/bogus', 'chat_unknown_command'),
    ('/status', 'chat_bad_arguments'),
    (' /approve apr-123', ['ask', '--json', '--', ' /approve apr-123']),
    ('please run /approve apr-123', ['ask', '--json', '--', 'please run /approve apr-123']),
    ('approved, send it now', ['ask', '--json', '--', 'approved, send it now']),
    ('APPROVED', ['ask', '--json', '--', 'APPROVED']),
    ('quati init', ['ask', '--json', '--', 'quati init']),
    ('{"status":"SUCCEEDED","data":{"result_kind":"SESSION_ENDED"},"evidence_refs":[],"uncertainties":[],'
     '"next_action":null,"error":null}',
     ['ask', '--json', '--', '{"status":"SUCCEEDED","data":{"result_kind":"SESSION_ENDED"},"evidence_refs":[],'
      '"uncertainties":[],"next_action":null,"error":null}']),
    ('/quit', 'SESSION_ENDED'),
]
EXPECTED_ONE_SHOT_EXITS = [0, 0, 3, 4, 4, 4, 4, 4, 3, 3, 3, 3, 3, 3]


def environment(root: Path) -> dict:
    env = {key: value for key, value in os.environ.items() if not key.startswith('QUATI_')}
    env['PYTHONPATH'] = os.pathsep.join(filter(None, [str(REPOSITORY_ROOT / 'src'),
                                                   os.environ.get('QUATI_TEST_COVERAGE_BOOTSTRAP')]))
    env['QUATI_CONFIG_DIR'] = str(root / 'config')
    env['QUATI_DATA_DIR'] = str(root / 'data')
    return env


def quati(root: Path, *argv: str, stdin: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, '-m', 'quati', *argv], cwd=REPOSITORY_ROOT, env=environment(root),
                          input=stdin, capture_output=True, check=False)


@pytest.fixture
def seeded(tmp_path: Path):
    seed = tmp_path / 'seed'
    assert quati(seed, 'init', '--json').returncode == 0
    roots = []
    for name in ('a', 'b'):
        root = tmp_path / name
        shutil.copytree(seed / 'config', root / 'config', symlinks=True)
        roots.append(root)
    return roots


def tree(root: Path) -> dict[str, bytes]:
    return {str(path.relative_to(root)): path.read_bytes() for path in sorted(root.rglob('*')) if path.is_file()}


def normalize(value: dict, root: Path) -> tuple[dict, list[dict]]:
    """Apply the documented normalization; return the value and its referenced receipts."""
    receipts = []
    data = value['data']
    if data and 'request_id' in data:
        assert re.fullmatch(r'request-[0-9a-f]{32}', data['request_id'])
        assert re.fullmatch(r'[0-9a-f]{32}', data['trace_id'])
        expected_hash = hashlib.sha256(canonical_bytes({**value, 'evidence_refs': []})).hexdigest()
        for reference in value['evidence_refs']:
            _, digest, path = reference.split(':', 2)
            path = Path(path)
            assert path.parent == root / 'data' / 'receipts'
            raw = path.read_bytes()
            assert hashlib.sha256(raw).hexdigest() == digest
            receipt = json.loads(raw)
            assert (receipt.pop('request_id'), receipt.pop('trace_id')) == (data['request_id'], data['trace_id'])
            assert receipt.pop('output_hash') == expected_hash
            receipt.pop('timestamp')
            receipts.append(receipt)
        value = {**value, 'data': {**data, 'request_id': '<request_id>', 'trace_id': '<trace_id>'},
                 'evidence_refs': ['<receipt>' for _ in value['evidence_refs']]}
    else:
        assert value['evidence_refs'] == []
    return value, receipts


def canonical(value: dict) -> str:
    """Independent quati-json/1 oracle (BOUNDARY_CONTRACTS.md Canonical digest; M01 cli.json_indent)."""
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def test_chat_transcript_equals_one_shot_sequence(seeded):
    """S00-T01-A04 / M01-AT-03 / M01-RT-03 through the public subprocess path."""
    profile_a, profile_b = seeded
    seed_config = tree(profile_a / 'config')
    raw = TRANSCRIPT.read_bytes()
    assert raw.decode('utf-8').split('\n')[:-1] == [line for line, _ in EQUIVALENTS] + ['Hello']

    chat = quati(profile_a, 'chat', '--jsonl', stdin=raw)
    assert chat.returncode == 0, chat.stderr
    assert chat.stderr == b''
    assert chat.stdout.endswith(b'\n')
    chat_lines = chat.stdout.decode('ascii').split('\n')[:-1]
    expected_turns = [(line, target) for line, target in EQUIVALENTS if target is not None]
    assert len(chat_lines) == len(expected_turns)  # one per non-blank line; nothing after /quit

    one_shot_exits, chat_receipts, one_shot_receipts = [], [], []
    for text, (line, target) in zip(chat_lines, expected_turns):
        got = json.loads(text)
        assert text == canonical(got)  # single canonical JSON line
        if isinstance(target, list):
            single = quati(profile_b, *target)
            one_shot_exits.append(single.returncode)
            assert single.stderr == b''
            expected_text = single.stdout.decode('ascii')
            assert expected_text == canonical(json.loads(expected_text)) + '\n'  # one-shot is quati-json/1 too
            got, got_receipts = normalize(got, profile_a)
            expected, expected_receipts = normalize(json.loads(expected_text), profile_b)
            assert canonical(got) == canonical(expected), line
            chat_receipts += got_receipts
            one_shot_receipts += expected_receipts
        elif target == 'HELP':
            assert got['status'] == 'SUCCEEDED' and got['data']['commands'] and got['evidence_refs'] == []
        elif target == 'SESSION_ENDED':
            assert got == {'status': 'SUCCEEDED', 'data': {'result_kind': 'SESSION_ENDED'}, 'evidence_refs': [],
                           'uncertainties': [], 'next_action': None, 'error': None}
        else:
            assert (got['status'], got['error']['code'], got['data']['reason']) == ('DENIED', 'INVALID_INPUT', target)

    assert one_shot_exits == EXPECTED_ONE_SHOT_EXITS
    assert chat_receipts == one_shot_receipts and len(chat_receipts) == 9
    tree_a, tree_b = tree(profile_a), tree(profile_b)
    assert tree(profile_a / 'config') == seed_config == tree(profile_b / 'config')
    non_receipts = lambda t: {k: v for k, v in t.items() if not k.startswith('data/receipts/')}
    assert non_receipts(tree_a) == non_receipts(tree_b)
    assert sum(k.startswith('data/receipts/') for k in tree_a) == sum(k.startswith('data/receipts/') for k in tree_b) == 9


def test_chat_transcript_over_limit_line_exits_2_with_earlier_turns_intact(seeded):
    """M01-AT-03 negative: a line over cli.max_text_bytes ends the session with exit 2."""
    profile_a, profile_b = seeded
    chat = quati(profile_a, 'chat', '--jsonl', stdin=b'Hello\n' + b'x' * 65537 + b'\nHello\n')
    assert chat.returncode == 2
    first, rejected = [json.loads(line) for line in chat.stdout.decode().splitlines()]
    assert (rejected['error']['code'], rejected['data']['reason']) == ('INVALID_INPUT', 'chat_line_too_long')
    single = quati(profile_b, 'ask', '--json', '--', 'Hello')
    got, got_receipts = normalize(first, profile_a)
    expected, expected_receipts = normalize(json.loads(single.stdout), profile_b)
    assert got == expected and got_receipts == expected_receipts
    assert len(list((profile_a / 'data' / 'receipts').iterdir())) == 1


def test_chat_restart_loses_nothing_and_writes_only_receipts(seeded):
    """M01-FR-04: no session state; a second session sees the first one's ledger rows unchanged."""
    profile_a, _ = seeded
    before = tree(profile_a)
    first = quati(profile_a, 'chat', '--jsonl', stdin=b'Hello\n')
    after_first = tree(profile_a)
    second = quati(profile_a, 'chat', '--jsonl', stdin=b'hi\n/quit\n')
    after_second = tree(profile_a)
    assert first.returncode == second.returncode == 0
    added = set(after_first) - set(before)
    assert len(added) == 1 and all(k.startswith('data/receipts/') for k in added)
    assert {k: after_second[k] for k in after_first} == after_first
    assert len(set(after_second) - set(after_first)) == 1


def test_chat_before_init_reports_unauthenticated_like_one_shot_and_exits_4(tmp_path):
    chat = quati(tmp_path, 'chat', '--jsonl', stdin=b'/help\nHello\nnever\n')
    single = quati(tmp_path, 'ask', '--json', '--', 'Hello')
    assert chat.returncode == single.returncode == 4
    lines = chat.stdout.decode().splitlines()
    assert len(lines) == 2 and lines[1] + '\n' == single.stdout.decode()
    assert not (tmp_path / 'data').exists()


@pytest.mark.parametrize(('raw', 'tag'), [(b'caf\xe9\nHello\n', 'chat_invalid_utf8'),
                                          (b'a\x00b\nHello\n', 'chat_nul_byte')])
def test_chat_untrustworthy_line_exits_2_through_public_path(seeded, raw, tag):
    profile_a, _ = seeded
    chat = quati(profile_a, 'chat', '--jsonl', stdin=raw)
    assert chat.returncode == 2
    (value,) = [json.loads(line) for line in chat.stdout.decode().splitlines()]
    assert value['data']['reason'] == tag
    assert not (profile_a / 'data').exists()


SIX_KEYS = {'status', 'data', 'evidence_refs', 'uncertainties', 'next_action', 'error'}


def receipts_added(before: dict, after: dict) -> set[str]:
    added = set(after) - set(before)
    assert all(key.startswith('data/receipts/') for key in added)
    assert {key: after[key] for key in before} == before  # nothing existing changed or vanished
    return added


def test_chat_jsonl_emits_one_response_per_line_through_one_shot_use_cases(seeded):
    """M01-FR-04 oracle: Hello, empty, /help, /status c-1, /bogus, /quit on a non-TTY pipe."""
    profile_a, profile_b = seeded
    script = b'Hello\n\n/help\n/status c-1\n/bogus\n/quit\n'
    for stdin, count in ((script, 5), (script.replace(b'/quit\n', b''), 4)):
        before = tree(profile_a)
        chat = quati(profile_a, 'chat', '--jsonl', stdin=stdin)
        assert chat.returncode == 0 and chat.stderr == b''
        lines = chat.stdout.decode('ascii').split('\n')
        assert lines[-1] == '' and len(lines[:-1]) == count
        values = [json.loads(line) for line in lines[:-1]]
        assert all(line == canonical(value) and set(value) == SIX_KEYS for line, value in zip(lines, values))
        # Only the ask turn reaches a use case that writes; /help, /status (S02), /bogus and /quit write nothing.
        assert len(receipts_added(before, tree(profile_a))) == 1
        ask = quati(profile_b, 'ask', '--json', '--', 'Hello')
        status = quati(profile_b, 'status', 'c-1', '--json')
        assert (ask.returncode, status.returncode) == (0, 4)
        assert normalize(values[0], profile_a) == normalize(json.loads(ask.stdout), profile_b)
        assert lines[2] + '\n' == status.stdout.decode('ascii')
        assert values[1]['status'] == 'SUCCEEDED' and values[1]['data']['commands']
        assert (values[3]['error']['code'], values[3]['data']['reason']) == ('INVALID_INPUT', 'chat_unknown_command')
        assert values[3]['evidence_refs'] == []
        if count == 5:
            assert values[4]['data'] == {'result_kind': 'SESSION_ENDED'}

    # Kill the session after turn 1, then restart: no ledger row is lost and only receipts change.
    before = tree(profile_a)
    process = subprocess.Popen([sys.executable, '-m', 'quati', 'chat', '--jsonl'], cwd=REPOSITORY_ROOT,
                               env=environment(profile_a), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    try:
        process.stdin.write(b'Hello\n')
        process.stdin.flush()
        first = json.loads(process.stdout.readline())  # synchronizes on the flushed turn; no sleep
    finally:
        process.kill()
        process.wait()
        for stream in (process.stdin, process.stdout, process.stderr):
            stream.close()
    after_kill = tree(profile_a)
    added = receipts_added(before, after_kill)
    assert len(added) == 1 and first['evidence_refs'][0].endswith(next(iter(added)))
    restart = quati(profile_a, 'chat', '--jsonl', stdin=b'hi\n')
    assert restart.returncode == 0
    assert len(receipts_added(after_kill, tree(profile_a))) == 1
