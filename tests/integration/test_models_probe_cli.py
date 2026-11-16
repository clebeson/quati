"""End-to-end ``quati models probe`` through the public entry point with a stand-in vendor executable.

The stand-in is a local script named ``claude`` placed first on PATH. It proves Quati's own
path (configuration, child-process isolation, parsing, receipt, exit codes). It is fake-provider
compatibility only and never evidence that the real Claude Code executable or a model works.
"""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from quati.adapters.providers import cli as cli_module
from quati.cli.main import main

SOURCE = Path(__file__).resolve().parents[2] / 'src'
KEY = 'synthetic-never-log'
# The child environment is an allow-list (M17), so the stand-in reads its log path and mode from files
# beside itself rather than from environment variables, which would never reach it.
STAND_IN = '''#!{python}
import json, os, re, sys
from pathlib import Path
here = Path(sys.argv[0]).resolve().parent
argv, prompt = sys.argv[1:], sys.stdin.read()
system = Path(argv[argv.index('--system-prompt-file') + 1]).read_text(encoding='utf-8')
with open(here / 'log.jsonl', 'a', encoding='utf-8') as log:
    log.write(json.dumps({{'argv': argv, 'cwd_entries': os.listdir('.'), 'env': sorted(os.environ),
                          'system': system}}) + '\\n')
mode = (here / 'mode').read_text(encoding='utf-8').strip() if (here / 'mode').exists() else 'ok'
if mode == 'fail':
    sys.exit(7)
nonce = (re.findall(r'[0-9a-f]{{16,}}', prompt) or [''])[-1]
# S00-T04 fix round 5 (S4): the probe names its target tool and field (the ask profile measures
# quati_search/query and the classification schema); the stand-in follows the instruction.
target = re.search(r'Call the tool (\\S+) with (\\S+) set to', prompt)
tool_name, field = (target.group(1), target.group(2)) if target else ('quati_probe_echo', 'nonce')
result = {{'type': 'result', 'subtype': 'success', 'is_error': False, 'result': nonce, 'total_cost_usd': 0.0001,
          'usage': {{'input_tokens': 1, 'output_tokens': 1}}, 'modelUsage': {{'stand-in-model': {{}}}}}}
if '--json-schema' in argv:
    schema = json.loads(argv[argv.index('--json-schema') + 1])
    if 'kind' in schema['properties']:
        result['structured_output'] = {{'kind': 'tool_call', 'tool_name': tool_name, 'text': '',
                                       'arguments_json': json.dumps({{field: 'wrong' if mode == 'liar' else nonce}})}}
    elif 'reason_code' in schema['properties']:
        result['structured_output'] = {{'intent': 'social', 'work_needed': False, 'complexity': 'trivial',
                                       'risk': 'none', 'uncertainty': 'low', 'safe_work_allowed': False,
                                       'next_action': 'respond', 'reason_code': nonce}}
    else:
        result['structured_output'] = {{'nonce': nonce}}
print(json.dumps(result))
'''


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    executable = bin_dir / 'claude'
    executable.write_text(STAND_IN.format(python=sys.executable), encoding='utf-8')
    executable.chmod(0o700)
    values = {'PATH': f'{bin_dir}{os.pathsep}{os.environ["PATH"]}', 'PYTHONPATH': str(SOURCE),
              'QUATI_CONFIG_DIR': str(tmp_path / 'config'), 'QUATI_DATA_DIR': str(tmp_path / 'data'),
              'QUATI_PROVIDER': 'claude_cli', 'QUATI_ALLOW_LIVE': '1', 'QUATI_API_KEY': KEY,
              'ANTHROPIC_API_KEY': 'stray-' + KEY}
    for name in ('QUATI_BASE_URL', 'QUATI_MODEL', 'QUATI_API_KEY_ENV'):
        monkeypatch.delenv(name, raising=False)
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    return tmp_path


def calls(workspace):
    return [json.loads(line) for line in (workspace / 'bin' / 'log.jsonl').read_text(encoding='utf-8').splitlines()]


def set_mode(workspace, mode):
    (workspace / 'bin' / 'mode').write_text(mode, encoding='utf-8')


def run_main(capsys, *arguments):
    code = main(list(arguments))
    return code, json.loads(capsys.readouterr().out)


def test_probe_through_the_installed_entry_point(workspace):
    completed = subprocess.run([sys.executable, '-m', 'quati', 'models', 'probe', '--json'], text=True,
                               capture_output=True, env=dict(os.environ))
    assert completed.returncode == 0, completed.stdout + completed.stderr
    value = json.loads(completed.stdout)
    report = value['data']['feature_report']
    assert (value['status'], report['transport'], report['model_or_adapter_version']) == (
        'SUCCEEDED', 'claude_cli', 'stand-in-model')
    assert report['features'] == {'tools': 'SUPPORTED', 'structured_output': 'SUPPORTED',
                                  'streaming': 'UNSUPPORTED', 'timeout': 'NOT_VERIFIED',
                                  'concurrency': 'NOT_VERIFIED'}
    assert report['observations'] == {'tools': 'PROBE_PASSED', 'structured_output': 'PROBE_PASSED',
                                      'streaming': 'STREAMING_UNSUPPORTED', 'timeout': 'DEADLINE_NOT_REACHED',
                                      'concurrency': 'CONCURRENCY_NOT_EXERCISED'}
    assert value['uncertainties'] == ['streaming: UNSUPPORTED (STREAMING_UNSUPPORTED)',
                                      'timeout: NOT_VERIFIED (DEADLINE_NOT_REACHED)',
                                      'concurrency: NOT_VERIFIED (CONCURRENCY_NOT_EXERCISED)']
    assert value['data']['provider']['status'] == 'PROBED'
    digest, path = value['evidence_refs'][0].split(':')[1:3]
    assert len(digest) == 64 and Path(path).is_file()
    assert KEY not in completed.stdout + completed.stderr + Path(path).read_text(encoding='utf-8')
    seen = calls(workspace)
    # tools, structured output and timeout; streaming never starts a process, and with the default
    # max_concurrency of 1 the concurrency check is not exercised
    assert len(seen) == 3
    for call in seen:
        assert call['argv'][0] == '-p' and call['argv'][call['argv'].index('--tools') + 1] == ''
        assert '--model=haiku' in call['argv'] and '--safe-mode' in call['argv']
        assert call['cwd_entries'] == [] and call['system']
        assert not {'QUATI_API_KEY', 'ANTHROPIC_API_KEY', 'PYTHONPATH'} & set(call['env'])
        assert not any(name.startswith('QUATI_') for name in call['env'])
        assert KEY not in json.dumps(call['argv'])


def test_probe_reports_a_wrong_nonce_and_a_failing_executable(workspace, monkeypatch, capsys):
    set_mode(workspace, 'liar')
    code, value = run_main(capsys, 'models', 'probe', '--json')
    assert code == 0 and value['data']['feature_report']['observations']['tools'] == 'NONCE_MISMATCH'
    assert value['data']['feature_report']['features']['tools'] == 'UNSUPPORTED'
    set_mode(workspace, 'fail')
    code, value = run_main(capsys, 'models', 'probe', '--json')
    assert (code, value['status'], value['error']['code']) == (5, 'UNAVAILABLE', 'TEMPORARILY_UNAVAILABLE')
    assert set(value['data']['feature_report']['observations'].values()) == {
        'CLI_FAILED', 'STREAMING_UNSUPPORTED', 'CONCURRENCY_NOT_EXERCISED'}


def test_probe_blocks_before_starting_any_process(workspace, monkeypatch, capsys):
    monkeypatch.delenv('QUATI_ALLOW_LIVE')
    code, value = run_main(capsys, 'models', 'probe', '--json')
    assert (code, value['status'], value['error']['code'], value['data']['provider']['reasons']) == (
        3, 'BLOCKED', 'NOT_CONFIGURED', ['LIVE_NOT_ALLOWED'])
    monkeypatch.setenv('QUATI_ALLOW_LIVE', '1')
    monkeypatch.setenv('PATH', str(workspace / 'empty'))
    code, value = run_main(capsys, 'models', 'probe', '--json')
    assert (code, value['status'], value['data']['provider']['reasons']) == (3, 'BLOCKED', ['CLI_NOT_FOUND'])
    monkeypatch.setenv('QUATI_PROVIDER', 'no-such-transport')
    code, value = run_main(capsys, 'models', 'probe', '--json')
    assert (code, value['status'], value['data']['provider']['reasons']) == (3, 'BLOCKED', ['TRANSPORT_UNKNOWN'])
    assert not (workspace / 'bin' / 'log.jsonl').exists()


def test_entry_point_argument_identity_and_resource_failures(workspace, monkeypatch, capsys):
    assert run_main(capsys, 'models', 'probe', '--no-such-option')[1]['error']['code'] == 'INVALID_INPUT'
    code, value = run_main(capsys, 'init', '--profile', 'corporate')
    assert (code, value['status'], value['error']['code']) == (2, 'DENIED', 'INVALID_INPUT')
    code, value = run_main(capsys, 'ask', 'hello', '--json')
    assert (code, value['status']) == (4, 'DENIED')
    assert run_main(capsys, 'init', '--json')[0] == 0
    assert run_main(capsys, 'doctor', '--json')[0] == 0
    assert run_main(capsys, 'ask', 'hello', '--json')[1]['status'] == 'SUCCEEDED'
    (workspace / 'blocked').write_text('', encoding='utf-8')
    monkeypatch.setenv('QUATI_DATA_DIR', str(workspace / 'blocked' / 'data'))
    code, value = run_main(capsys, 'models', 'probe', '--json')
    assert (code, value['status'], value['error']['code']) == (1, 'BLOCKED', 'INTERNAL_ERROR')  # M01 exit table


def test_run_process_really_kills_a_child_that_outlives_its_deadline(tmp_path):
    marker = tmp_path / 'survived'
    script = f'import time; time.sleep(60); open({str(marker)!r}, "w").close()'
    with pytest.raises(TimeoutError):
        cli_module.run_process([sys.executable, '-c', script], '', 0.2, str(tmp_path), {})
    assert not marker.exists()
