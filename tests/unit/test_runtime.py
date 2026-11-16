"""L1 public-path checks; no live model or durability claims."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import sys

from quati.application.ports import ProviderConfig


def cli(*args):
    with tempfile.TemporaryDirectory(prefix='quati-cli-regression-') as temporary:
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / 'src'),
                   QUATI_CONFIG_DIR=temporary + '/config', QUATI_DATA_DIR=temporary + '/data')
        for key in ['QUATI_BASE_URL', 'QUATI_MODEL', 'QUATI_API_KEY_ENV', 'QUATI_ALLOW_LIVE']:
            env.pop(key, None)
        command = [sys.executable, '-m', 'quati']
        if args[0] == 'ask':
            initialized = subprocess.run(command + ['init', '--json'], env=env, text=True, capture_output=True)
            assert initialized.returncode == 0, initialized.stderr
        result = subprocess.run(command + list(args), env=env, text=True, capture_output=True)
        return result.returncode, json.loads(result.stdout)


def test_m01_doctor_missing_provider_is_honest():
    code, value = cli('doctor', '--json')
    assert code == 0
    assert value['data']['provider']['configured'] is False
    assert value['data']['provider']['features']['tools'] == 'NOT_VERIFIED'


def test_m01_greeting_creates_no_job():
    code, value = cli('ask', 'Good morning.', '--json')
    assert code == 0
    assert value['status'] == 'SUCCEEDED' and value['data']['result_status'] == 'RESPONDED'
    assert value['data']['commitment_id'] is None
    assert value['data']['tool_calls'] == []


def test_m01_mixed_greeting_work_not_silently_dropped():
    code, value = cli('ask', 'Hello, investigate conversion differences.', '--json')
    assert code == 3
    assert value['status'] == 'BLOCKED'
    assert value['data']['commitment_id'] is None


def test_m26_default_receipts_exclude_raw_input_and_secret(tmp_path, monkeypatch):
    from quati.application.cli_service import CLIService
    from quati.adapters.local_identity import LocalIdentity
    from quati.adapters.evidence import write_receipt
    monkeypatch.setenv('QUATI_DATA_DIR', str(tmp_path / 'data'))
    monkeypatch.setenv('QUATI_API_KEY_ENV', 'SECRET_TEST_KEY')
    monkeypatch.setenv('SECRET_TEST_KEY', 'never-store-this')
    identity = LocalIdentity(tmp_path / 'config')
    identity.initialize()
    code, value = CLIService(identity, ProviderConfig(), write_receipt).ask('Investigate private customer never-store-this')
    path = next((tmp_path / 'data' / 'receipts').glob('*.json'))
    raw = path.read_text()
    assert code == 3 and 'private customer' not in raw and 'never-store-this' not in raw
    assert path.stat().st_mode & 0o777 == 0o600
    assert value['evidence_refs'][0].startswith('sha256:')


def test_independent_doctor_rejects_invalid_port_and_url_credentials(monkeypatch):
    from quati.application.cli_service import config_diagnostics
    monkeypatch.setenv('SYNTHETIC_KEY','test-only')
    for endpoint in ['https://example.test:bad/v1', 'https://user:pass@example.test/v1', 'https://example.test/\nsecret']:
        assert not config_diagnostics(ProviderConfig(endpoint,'model','SYNTHETIC_KEY',True))['configured']


def test_independent_advisory_classification_cannot_claim_work_completed(tmp_path, monkeypatch):
    """The unqualified work path cannot publish advisory model prose as completion.

    Re-test advisory model output at S00-T04 when that path is enabled; this local
    contribution does not close the preserved candidate false-completion bug.
    """
    from quati.application.cli_service import CLIService
    from quati.adapters.local_identity import LocalIdentity
    from quati.adapters.evidence import write_receipt
    monkeypatch.setenv('QUATI_DATA_DIR', str(tmp_path / 'data'))
    identity = LocalIdentity(tmp_path / 'config')
    identity.initialize()
    code, result = CLIService(identity, ProviderConfig(), write_receipt).ask('Investigate why conversions fell.')
    assert code != 0 and result['status'] == 'BLOCKED'
    assert result['data']['commitment_id'] is None
    assert 'completed the investigation' not in str(result)
