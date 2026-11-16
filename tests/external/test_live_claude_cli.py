"""Live authenticated smoke of the ``claude_cli`` transport through the public entry point.

This lane contacts a real model through the operator's own signed-in Claude Code executable and
spends real money (a fraction of a US cent per run with the ``haiku`` model). It runs only when the
operator opts in with ``QUATI_LIVE_SMOKE=claude_cli``; otherwise it is reported as skipped, which is
``NOT_VERIFIED_EXTERNAL`` and never a pass. It proves this one transport only.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

SOURCE = Path(__file__).resolve().parents[2] / 'src'
OPTED_IN = os.environ.get('QUATI_LIVE_SMOKE') == 'claude_cli'

pytestmark = [pytest.mark.live,
              pytest.mark.skipif(not OPTED_IN, reason='NOT_VERIFIED_EXTERNAL: set QUATI_LIVE_SMOKE=claude_cli'),
              pytest.mark.skipif(OPTED_IN and not shutil.which('claude'),
                                 reason='NOT_VERIFIED_EXTERNAL: claude executable not found')]


def test_real_claude_cli_probe(tmp_path):
    # A minimal environment: the operator's sign-in lives under HOME (or CLAUDE_CONFIG_DIR); nothing else is needed.
    environment = {name: os.environ[name] for name in ('PATH', 'HOME', 'USER', 'LANG', 'TERM', 'CLAUDE_CONFIG_DIR')
                   if name in os.environ}
    environment.update(QUATI_CONFIG_DIR=str(tmp_path / 'config'), QUATI_DATA_DIR=str(tmp_path / 'data'),
                       QUATI_PROVIDER='claude_cli', QUATI_MODEL='haiku', QUATI_ALLOW_LIVE='1',
                       PYTHONPATH=str(SOURCE))
    done = subprocess.run([sys.executable, '-m', 'quati', 'models', 'probe', '--json'], env=environment,
                          capture_output=True, text=True, timeout=600)
    assert done.returncode == 0, done.stdout
    value = json.loads(done.stdout)
    report = value['data']['feature_report']
    assert value['status'] == 'SUCCEEDED' and value['error'] is None
    assert report['transport'] == 'claude_cli' and 'haiku' in report['model_or_adapter_version']
    assert report['observations'] == {
        'tools': 'PROBE_PASSED', 'structured_output': 'PROBE_PASSED', 'streaming': 'STREAMING_UNSUPPORTED',
        'timeout': 'PROBE_PASSED', 'concurrency': 'CONCURRENCY_NOT_EXERCISED'}
    digest, path = value['evidence_refs'][0].split(':', 2)[1:]
    assert Path(path).is_file() and len(digest) == 64
