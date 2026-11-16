"""S00-T01 public CLI contract tests (M01, M02, M26 contribution coverage).

These tests exercise the installed module entry point in isolated LOCAL paths.
They never configure a provider or read provider credentials.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import jsonschema
import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_CONTRACT_PATH = REPOSITORY_ROOT / "contracts" / "runtime-boundaries.schema.json"


@pytest.fixture
def run_cli(tmp_path: Path):
    """Return an isolated subprocess caller with provider settings removed."""
    config_dir = tmp_path / "config"
    data_dir = tmp_path / "data"
    env = os.environ.copy()
    for name in (
        "QUATI_BASE_URL",
        "QUATI_MODEL",
        "QUATI_ALLOW_LIVE",
        "QUATI_API_KEY_ENV",
        "QUATI_API_KEY",
    ):
        env.pop(name, None)
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(REPOSITORY_ROOT / "src"),
                                                   os.environ.get("QUATI_TEST_COVERAGE_BOOTSTRAP")]))
    env["QUATI_CONFIG_DIR"] = str(config_dir)
    env["QUATI_DATA_DIR"] = str(data_dir)

    def call(*arguments: str) -> tuple[subprocess.CompletedProcess[str], dict]:
        completed = subprocess.run(
            [sys.executable, "-m", "quati", *arguments],
            cwd=REPOSITORY_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        try:
            response = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            pytest.fail(
                "CLI did not return JSON on --json path; "
                f"exit={completed.returncode}, stderr={completed.stderr!r}"
            )
        return completed, response

    return call


def assert_response(response: dict) -> None:
    """Validate the exact public Response envelope from the boundary schema."""
    contract = json.loads(RUNTIME_CONTRACT_PATH.read_text(encoding="utf-8"))
    schema = {
        "$schema": contract["$schema"],
        "$ref": "#/$defs/Response",
        "$defs": contract["$defs"],
    }
    jsonschema.validate(response, schema)


def assert_error(response: dict, status: str, code: str) -> None:
    assert_response(response)
    assert response["status"] == status
    assert response["error"]["code"] == code


def test_a01(run_cli):
    """M01-FR-01/AT-01: doctor is safe before init and reports unverified features."""
    before, diagnostic = run_cli("doctor", "--json")
    assert before.returncode == 0
    assert_response(diagnostic)
    assert diagnostic["status"] == "SUCCEEDED"
    assert diagnostic["data"]["provider"]["configured"] is False
    assert diagnostic["data"]["identity"]["initialized"] is False
    assert diagnostic["data"]["provider"]["features"]
    assert set(diagnostic["data"]["provider"]["features"].values()) == {
        "NOT_VERIFIED"
    }

    initialized, init_response = run_cli("init", "--json")
    assert initialized.returncode == 0
    assert_response(init_response)
    assert init_response["status"] == "SUCCEEDED"

    after, diagnostic = run_cli("doctor", "--json")
    assert after.returncode == 0
    assert_response(diagnostic)
    assert diagnostic["data"]["provider"]["configured"] is False
    assert diagnostic["data"]["identity"]["initialized"] is True


def test_a02(run_cli):
    """S00-T01 A02; IDN-01 contribution: pre-init ask is denied, greeting is local."""
    denied, response = run_cli("ask", "Hello.", "--json")
    assert denied.returncode == 4
    assert_error(response, "DENIED", "UNAUTHENTICATED")

    initialized, _ = run_cli("init", "--json")
    assert initialized.returncode == 0

    greeted, response = run_cli("ask", "Hello.", "--json")
    assert greeted.returncode == 0
    assert_response(response)
    assert response["status"] == "SUCCEEDED"
    assert response["data"]["result_status"] == "RESPONDED"
    assert response["data"]["commitment_id"] is None
    assert response["data"]["tool_calls"] == []
    assert response["data"]["provider_used"] is False
    assert isinstance(response["data"]["text"], str)
    assert response["data"]["text"]


def test_a03(run_cli):
    """S00-T01 A03: mixed input is not swallowed by the exact-greeting path."""
    initialized, _ = run_cli("init", "--json")
    assert initialized.returncode == 0

    blocked, response = run_cli(
        "ask", "Hello, please summarize tomorrow's calendar.", "--json"
    )
    assert blocked.returncode == 3
    assert_error(response, "BLOCKED", "NOT_CONFIGURED")
    assert response["data"]["commitment_id"] is None
    assert response["data"]["provider_used"] is False


@pytest.mark.parametrize(
    "arguments",
    [
        ("ask", "", "--json"),
        ("ask", "é" * 32769, "--json"),  # 65538 bytes > M01 cli.max_text_bytes (LOG-0019)
        ("does-not-exist", "--json"),
    ],
)
def test_invalid_or_unsupported_cli_input_returns_typed_error(run_cli, arguments):
    """Invalid input has a sanitized envelope, never a parser traceback."""
    completed, response = run_cli(*arguments)
    assert completed.returncode == 2
    assert_error(response, "DENIED", "INVALID_INPUT")
    assert "Traceback" not in completed.stderr


def test_doctor_probe_without_provider_is_not_configured(run_cli):
    """Provider probe is explicit and cannot imply support without configuration."""
    completed, response = run_cli("doctor", "--probe", "--json")
    assert completed.returncode == 3
    assert_error(response, "BLOCKED", "NOT_CONFIGURED")
    assert response["data"]["provider"]["configured"] is False


def test_init_accepts_documented_local_profile_and_denies_unavailable_server(run_cli):
    denied, result = run_cli('init', '--profile', 'server', '--json')
    assert denied.returncode == 2
    assert_error(result, 'DENIED', 'INVALID_INPUT')
    diagnostic, result = run_cli('doctor', '--json')
    assert diagnostic.returncode == 0
    assert result['data']['identity']['initialized'] is False
    initialized, result = run_cli('init', '--profile', 'local', '--json')
    assert initialized.returncode == 0
    assert_response(result)


def test_receipt_filesystem_failure_does_not_claim_success(run_cli, tmp_path):
    initialized, _ = run_cli('init', '--json')
    assert initialized.returncode == 0
    # init now writes its policy.changed receipt (RFC-014 §5.1, LOG-0021), so occupy the receipts path instead.
    receipts = tmp_path / 'data' / 'receipts'
    if receipts.is_dir():
        for item in receipts.iterdir():
            item.unlink()
        receipts.rmdir()
    receipts.write_text('occupied path')
    failed, result = run_cli('ask', 'Hello.', '--json')
    # Fix round 7 (LOG-0041 N1): an unusable receipts path is found before the request is handled and is the
    # typed local-storage refusal (M01 exit 4); until then it was INTERNAL_ERROR, exit 1, after the fact.
    assert failed.returncode == 4
    assert_error(result, 'UNAVAILABLE', 'TEMPORARILY_UNAVAILABLE')
    assert result['data'] == {'reason': 'state_dir_unsafe', 'component': 'receipts'}
    assert result['evidence_refs'] == []
    assert 'Traceback' not in failed.stderr
