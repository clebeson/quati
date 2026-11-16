"""Independent L1 adversarial review of M01/M02 boundary and integrity contracts."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

from quati.application.identity import AccessDenied, LocalToken, canonical_bytes, verify_token

ROOT = Path(__file__).resolve().parents[2]


def run_cli(directory, *arguments, extra_env=None):
    env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'), QUATI_CONFIG_DIR=str(directory),
               QUATI_DATA_DIR=str(directory.parent / 'receipts'))
    for name in ('QUATI_BASE_URL', 'QUATI_MODEL', 'QUATI_ALLOW_LIVE', 'QUATI_API_KEY_ENV', 'QUATI_API_KEY'):
        env.pop(name, None)
    env.update(extra_env or {})
    return subprocess.run([sys.executable, '-m', 'quati', *arguments], cwd=ROOT, env=env,
                          capture_output=True, text=True, timeout=3)


@pytest.mark.parametrize('corruption', ['null', '42', '"broken-record"'])
def test_idn01_corrupt_scalar_credentials_fail_closed_in_public_cli(tmp_path, corruption):
    """A valid JSON scalar is still an invalid credential, never an uncaught exception."""
    directory = tmp_path / 'config'
    directory.mkdir(mode=0o700)
    record = directory / 'identity.json'
    record.write_text(corruption)
    record.chmod(0o600)
    diagnostic = run_cli(directory, 'doctor', '--json')
    assert diagnostic.returncode == 0
    assert 'Traceback' not in diagnostic.stderr
    assert json.loads(diagnostic.stdout)['data']['identity']['initialized'] is False
    denied = run_cli(directory, 'ask', 'Hello.', '--json')
    assert denied.returncode == 4
    assert json.loads(denied.stdout)['error']['code'] == 'UNAUTHENTICATED'


def test_m01_corrupt_fifo_credential_does_not_hang_doctor(tmp_path):
    """A nonregular local credential must be rejected without a blocking FIFO read."""
    directory = tmp_path / 'config'
    directory.mkdir(mode=0o700)
    os.mkfifo(directory / 'identity.json', mode=0o600)
    diagnostic = run_cli(directory, 'doctor', '--json')
    assert diagnostic.returncode == 0
    assert json.loads(diagnostic.stdout)['data']['identity']['initialized'] is False


def test_m26_canonical_digest_escapes_unicode_per_quati_json_v1():
    assert canonical_bytes({'greeting': 'Olá'}) == b'{"greeting":"Ol\\u00e1"}'


@pytest.mark.parametrize('invalid', [float('nan'), float('inf'), float('-inf')])
def test_m26_canonical_digest_rejects_nonfinite_values(invalid):
    with pytest.raises(ValueError):
        canonical_bytes({'value': invalid})


@pytest.mark.parametrize('mutation', ['invalid_sub', 'invalid_tid', 'fractional_expiry', 'unknown_property'])
def test_idn01_signed_claims_still_require_the_typed_contract(mutation):
    """A real valid signature does not make malformed token fields schema-valid."""
    now = int(time.time())
    claims = {'iss': 'quati-local', 'sub': '01ARZ3NDEKTSV4RRFFQ69G5FAV',
              'tid': '01ARZ3NDEKTSV4RRFFQ69G5FAW', 'pkind': 'HUMAN', 'aud': 'quati-local',
              'scope': 'quati:converse quati:work.read', 'exp': now + 600, 'iat': now,
              'nbf': now, 'jti': '0123456789abcdef', 'sid': 'session',
              'amr': ['local_os', 'device_key'], 'auth_time': now, 'client_id': 'quati-cli'}
    if mutation == 'invalid_sub':
        claims['sub'] = 'display-name-from-untrusted-input'
    elif mutation == 'invalid_tid':
        claims['tid'] = 123
    elif mutation == 'fractional_expiry':
        claims['exp'] = now + 599.5
    else:
        claims['unregistered_claim'] = 'untrusted metadata'
    key = Ed25519PrivateKey.generate()
    token = LocalToken(claims, key.sign(canonical_bytes(claims)))
    with pytest.raises(AccessDenied):
        verify_token(token, key.public_key().public_bytes_raw())


@pytest.mark.parametrize('synthetic_secret', ['SUCCEEDED', 'false', 'status'])
def test_m26_redaction_preserves_structural_status_enum(tmp_path, synthetic_secret):
    """A synthetic key value matching an enum must not rewrite the public envelope."""
    diagnostic = run_cli(tmp_path / 'config', 'doctor', '--json',
                         extra_env={'QUATI_API_KEY_ENV': 'REVIEW_SECRET_REF',
                                    'REVIEW_SECRET_REF': synthetic_secret})
    assert diagnostic.returncode == 0
    assert json.loads(diagnostic.stdout)['status'] == 'SUCCEEDED'
