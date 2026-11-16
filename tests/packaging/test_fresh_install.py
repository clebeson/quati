"""M01-AT-01: a fresh LOCAL profile with no provider variables runs ``quati doctor --json``.

Proof tier: L2 for the source-checkout legs (the real module entry point in a clean child process
and a fresh temporary profile). The installed-wheel leg builds and installs the wheel into an
empty target directory; it needs the declared build backend (``setuptools``) to be importable
without network access and is skipped, with the reason, when it is not. A skipped wheel leg
leaves the fresh-wheel qualification NOT VERIFIED; the checkout legs never stand in for it.
"""

from __future__ import annotations

import importlib.util
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from quati.application.ports import ProviderConfig
from quati.cli import main as cli_main

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PROVIDER_VARIABLES = ('QUATI_BASE_URL', 'QUATI_MODEL', 'QUATI_ALLOW_LIVE', 'QUATI_API_KEY_ENV', 'QUATI_API_KEY',
                      'QUATI_PROVIDER', 'QUATI_LIVE_EVAL', 'ANTHROPIC_API_KEY', 'OPENAI_API_KEY')
BACKEND_MISSING = importlib.util.find_spec('setuptools') is None


def fresh_environment(profile: Path, python_path: str) -> dict:
    env = {name: value for name, value in os.environ.items()
           if name not in PROVIDER_VARIABLES and (not name.startswith('QUATI_')
                                                  or name == 'QUATI_TEST_COVERAGE_BOOTSTRAP')}
    env['PYTHONPATH'] = os.pathsep.join(filter(None, [python_path, os.environ.get('QUATI_TEST_COVERAGE_BOOTSTRAP')]))
    env['HOME'] = str(profile)
    env['QUATI_CONFIG_DIR'] = str(profile / 'config')
    env['QUATI_DATA_DIR'] = str(profile / 'data')
    return env


def assert_fresh_report(completed: subprocess.CompletedProcess, profile: Path) -> dict:
    assert completed.returncode == 0, completed.stderr
    lines = completed.stdout.splitlines()
    assert len(lines) == 1 and completed.stderr == ''
    value = json.loads(lines[0])
    data = value['data']
    assert value['status'] == 'SUCCEEDED' and value['error'] is None
    assert data['provider']['status'] == 'NOT_CONFIGURED' and data['provider']['configured'] is False
    assert data['provider']['measured_support'] == 'NOT_VERIFIED'
    assert set(data['provider']['features'].values()) == {'NOT_VERIFIED'}
    assert data['live_calls_allowed'] is False
    assert data['listening_sockets'] == 0
    assert data['profile'] == 'LOCAL' and data['os'] == platform.system()
    # Linux is the reference OS; any other OS stays NOT_VERIFIED until its own qualification run.
    assert data['os_qualification'] == ('QUALIFIED' if platform.system() == 'Linux' else 'NOT_VERIFIED')
    assert data['worker']['status'] == 'NOT_APPLICABLE'
    assert data['identity']['initialized'] is False
    assert not profile.exists() or not any(path.is_file() for path in profile.rglob('*'))   # doctor wrote nothing
    return data


def test_doctor_reports_provider_not_configured(tmp_path: Path, monkeypatch, capsys) -> None:
    profile = tmp_path / 'profile'
    completed = subprocess.run([sys.executable, '-m', 'quati', 'doctor', '--json'], cwd=tmp_path, text=True,
                               env=fresh_environment(profile, str(REPOSITORY_ROOT / 'src')), capture_output=True)
    data = assert_fresh_report(completed, profile)
    assert 'API_KEY_MISSING' in data['provider']['reasons'] and 'LIVE_NOT_ALLOWED' in data['provider']['reasons']

    # Negative: the live allowance without a base URL is still NOT_CONFIGURED and opens no connection.
    # The allowance is injected as configuration; this test never sets the live-allowance variable.
    for name in PROVIDER_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('QUATI_CONFIG_DIR', str(profile / 'config'))
    monkeypatch.setenv('QUATI_DATA_DIR', str(profile / 'data'))
    monkeypatch.setattr(cli_main, '_config', lambda: ProviderConfig(transport='openai_compatible', allow_live=True))
    connections = []

    def spy(self, address, *args):
        connections.append(address)
        raise AssertionError('doctor must not open a network connection')

    monkeypatch.setattr(socket.socket, 'connect', spy)
    monkeypatch.setattr(socket.socket, 'connect_ex', spy)
    monkeypatch.setattr(socket, 'create_connection', lambda *args, **kwargs: spy(None, args[0]))
    monkeypatch.setattr(socket, 'getaddrinfo', lambda *args, **kwargs: spy(None, args[0]))
    code = cli_main.main(['doctor', '--json'])
    value = json.loads(capsys.readouterr().out)
    provider = value['data']['provider']
    assert (code, provider['status'], provider['configured']) == (0, 'NOT_CONFIGURED', False)
    assert provider['reasons'][0] == 'ENDPOINT_INVALID' and value['data']['live_calls_allowed'] is True
    assert connections == []


@pytest.mark.skipif(BACKEND_MISSING, reason=(
    'fresh-wheel install NOT VERIFIED here: the build backend declared in pyproject.toml (setuptools>=75) is not '
    'importable in this environment and no package index is reachable offline'))
def test_doctor_from_a_freshly_installed_wheel(tmp_path: Path) -> None:
    """Build the wheel, install it alone into an empty directory and run it from there.

    The wheel is built from a copy of the packaged inputs (pyproject.toml, src/, contracts/, examples/), so
    the build leaves nothing in the repository. The installed copy has no repository beside it: the contract
    schemas, the active behavior package and the default LOCAL policy must come from its package data
    (``quati/assets``), and they must compile to the repository's reference hashes.
    """
    project, wheels, target, profile = tmp_path / 'project', tmp_path / 'wheels', tmp_path / 'site', tmp_path / 'profile'
    project.mkdir()
    shutil.copy2(REPOSITORY_ROOT / 'pyproject.toml', project / 'pyproject.toml')
    for name in ('src', 'contracts', 'examples'):
        shutil.copytree(REPOSITORY_ROOT / name, project / name, ignore=shutil.ignore_patterns('__pycache__', '*.egg-info'))
    pip = [sys.executable, '-m', 'pip', '--disable-pip-version-check', '--no-input']
    subprocess.run([*pip, 'wheel', '--no-deps', '--no-index', '--no-build-isolation', '--wheel-dir', str(wheels),
                    str(project)], check=True, capture_output=True, cwd=tmp_path)
    wheel, = wheels.glob('quati-*.whl')
    subprocess.run([*pip, 'install', '--no-deps', '--no-index', '--target', str(target), str(wheel)], check=True,
                   capture_output=True, cwd=tmp_path)
    shutil.rmtree(project)                                        # nothing but the installed copy remains
    environment = fresh_environment(profile, str(target))
    probe = subprocess.run([sys.executable, '-c', 'import quati; print(quati.__file__)'], cwd=tmp_path, text=True,
                           env=environment, capture_output=True, check=True)
    assert Path(probe.stdout.strip()).is_relative_to(target)      # the wheel copy runs, not the checkout
    assert (target / 'quati' / 'assets' / 'contracts' / 'behavior-package.schema.json').is_file()

    def quati(*argv: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, '-m', 'quati', *argv], cwd=tmp_path, text=True, env=environment,
                              capture_output=True)
    data = assert_fresh_report(quati('doctor', '--json'), profile)
    reference = json.loads((REPOSITORY_ROOT / 'examples' / 'behavior' / 'compiled_receipt.reference.json').read_bytes())
    assert data['behavior']['status'] == 'VALID'
    assert {name: data['behavior'][name] for name in ('behavior_hash', 'statechart_hash', 'prompt_hash')} == {
        name: reference[name] for name in ('behavior_hash', 'statechart_hash', 'prompt_hash')}
    initialized = quati('init', '--json')
    assert initialized.returncode == 0 and json.loads(initialized.stdout)['data']['policy']['action'] == 'INSTALLED'
    greeting = quati('ask', 'Hello', '--json')
    assert greeting.returncode == 0 and json.loads(greeting.stdout)['data']['result_kind'] == 'GREETING'
