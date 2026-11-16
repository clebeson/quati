"""Test-only harness of the fix round 8 tests: one isolated LOCAL profile driven through real child processes.

``Profile.quati`` runs the product exactly as installed (``python -m quati``; no fake provider can
be selected there, proof tier L2). ``Profile.model`` runs the public ``main`` in a fresh process
whose model is the SCRIPTED FAKE of ``s00_fix8_runner.py`` (the adversary; never evidence of a real
provider). No network, no ``QUATI_ALLOW_LIVE``.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import quati

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = Path(quati.__file__).resolve().parents[1]      # the tree under test; the children import the same one
RUNNER = Path(__file__).resolve().parent / "s00_fix8_runner.py"
PYTHON = str(Path(sys.executable).absolute())
CAPABILITY = "fixtures.calendar-read"
READ = [["search", "next appointment calendar"], ["describe", CAPABILITY], ["invoke", CAPABILITY, {"limit": 1}],
        ["final", "done"]]
CLAIM = "Done. All events were deleted and the board was notified. Verified by audit record AUD-991."


class Profile:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.config, self.data = root / "config", root / "data"
        self.harness = root / "harness"
        self.harness.mkdir(parents=True)
        self.spy = self.harness / "spy.jsonl"
        self.runs = 0

    def environment(self) -> dict:
        environment = {"PATH": "/usr/bin:/bin", "PYTHONPATH": str(SOURCE_ROOT), "HOME": str(self.root),
                       "QUATI_CONFIG_DIR": str(self.config), "QUATI_DATA_DIR": str(self.data),
                       "PYTHONDONTWRITEBYTECODE": "1"}
        if "COVERAGE_PROCESS_START" in os.environ:      # opt-in subprocess coverage (tests/coverage/sitecustomize.py)
            environment["COVERAGE_PROCESS_START"] = os.environ["COVERAGE_PROCESS_START"]
            environment["PYTHONPATH"] += os.pathsep + str(REPOSITORY_ROOT / "tests" / "coverage")
            for name in ("QUATI_TEST_COVERAGE_LIBRARY", "COVERAGE_FILE"):
                if name in os.environ:
                    environment[name] = os.environ[name]
        return environment

    def _run(self, command: list, stdin: bytes | None = None):
        completed = subprocess.run(command, capture_output=True, env=self.environment(), timeout=180, check=False,
                                   input=stdin)
        assert completed.stderr == b"", completed.stderr
        return completed.returncode, completed.stdout.decode("utf-8")

    def quati(self, *argv: str, stdin: bytes | None = None):
        """The product CLI exactly as installed; raw stdout."""
        self.spy.unlink(missing_ok=True)
        return self._run([PYTHON, "-m", "quati", *argv], stdin)

    def model(self, script: list, *argv: str, stdin: bytes | None = None):
        """The public CLI in a fresh process whose model is the scripted adversary; raw stdout."""
        self.runs += 1
        scenario = self.harness / f"scenario-{self.runs}.json"
        scenario.write_text(json.dumps({"script": script}), encoding="utf-8")
        self.spy.unlink(missing_ok=True)
        return self._run([PYTHON, str(RUNNER), str(self.spy), str(scenario), *argv], stdin)

    def run(self, script: list | None, *argv: str, stdin: bytes | None = None):
        """``script`` None: the plain product CLI with no provider configured."""
        return self.quati(*argv, stdin=stdin) if script is None else self.model(script, *argv, stdin=stdin)

    def ask(self, script: list | None, text: str):
        code, output = self.run(script, "ask", "--json", "--", text)
        return code, json.loads(output), output

    def chat(self, script: list | None, lines: list[str]):
        """One ``quati chat --jsonl`` session: one Response per input line."""
        code, output = self.run(script, "chat", "--jsonl", stdin="".join(f"{line}\n" for line in lines).encode())
        values = [json.loads(line) for line in output.splitlines()]
        assert len(values) == len(lines), output
        return code, values, output

    def spied(self, kind: str) -> list:
        if not self.spy.exists():
            return []
        return [entry[1] for entry in (json.loads(line) for line in self.spy.read_text().splitlines())
                if entry[0] == kind]

    def audit(self) -> list[dict]:
        path = self.data / "capabilities" / "audit.jsonl"
        return [json.loads(line) for line in path.read_bytes().splitlines() if line] if path.exists() else []

    def receipt_names(self) -> list[str]:
        directory = self.data / "receipts"
        return sorted(path.name for path in directory.iterdir()) if directory.exists() else []


def new_profile(root: Path, *, probed: bool = True) -> Profile:
    """``quati init``, one ENABLED read fixture and (``probed``) a probed scripted model (tools SUPPORTED)."""
    workspace = Profile(root)
    code, output = workspace.quati("init", "--json")
    assert code == 0, output
    code, output = workspace.quati("capabilities", "install-fixture", CAPABILITY.split(".")[1], "--enable-fixture",
                                   "--json")
    assert code == 0 and json.loads(output)["data"]["lifecycle"] == "ENABLED"
    if probed:
        code, output = workspace.model([], "models", "probe", "--json")
        assert code == 0 and json.loads(output)["data"]["feature_report"]["features"]["tools"] == "SUPPORTED"
    return workspace


def receipt(value: dict) -> dict:
    _, sha256, path = value["evidence_refs"][0].split(":", 2)
    raw = Path(path).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == sha256
    return json.loads(raw)


def stable(value: dict) -> dict:
    """A Response without the per-request identifiers and the receipt reference."""
    data = {key: item for key, item in value["data"].items() if key not in ("request_id", "trace_id")}
    return {**value, "data": data, "evidence_refs": []}


def steps(value: dict) -> list[tuple]:
    return [(step["operation"], step["status"], step["reason"], step["handler_executed"])
            for step in value["data"]["tool_calls"]]


def social_data(reply: str) -> dict:
    """The whole ``data`` object of a social-only answer, without the request and trace ids."""
    return {"commitment_id": None, "scope": "S00_T01_LOCAL_CLI", "provider_used": False, "tool_calls": [],
            "usage": {"cost_usd": None}, "received": True, "launched": False, "delivered": False,
            "result_status": "RESPONDED", "result_kind": "GREETING", "text": reply,
            "text_source": "application_template", "display_lines": [reply], "work_performed": False,
            "actions_taken": []}
