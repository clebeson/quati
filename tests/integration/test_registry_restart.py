"""REG-05 (RFC-015; M14-AT-01, M15-FR-01, K7), L2: discoverable after a real process restart.

The restart is a fresh Python process over the same temporary state directory. The
public ``quati capabilities`` CLI is outside the S00-T03 owned paths, so the process
uses the application/adapters entry path that the CLI will call.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
UNIT = REPOSITORY_ROOT / "tests" / "unit"
sys.path.insert(0, str(UNIT))

from s00_t03_support import build  # noqa: E402

SEARCH_SCRIPT = """
import json, sys
from pathlib import Path
from s00_t03_support import build
harness = build(Path(sys.argv[1]))
turn = harness.turn()
found = {query: [c["capability_id"] for c in turn.search(turn.context, query).data["candidates"]]
         for query in sys.argv[2:]}
print(json.dumps({"found": found, "records": len(harness.registry.records(harness.operator))}))
"""


def _new_process_search(root: Path, *queries: str) -> dict:
    environment = {"PATH": "/usr/bin:/bin", "PYTHONPATH": os.pathsep.join([str(REPOSITORY_ROOT / "src"), str(UNIT)]),
                   "HOME": str(root)}
    completed = subprocess.run([sys.executable, "-c", SEARCH_SCRIPT, str(root), *queries], capture_output=True,
                               text=True, env=environment, timeout=120, check=True)
    return json.loads(completed.stdout)


def _hashes() -> tuple[str, str]:
    code = hashlib.sha256()
    for path in sorted((REPOSITORY_ROOT / "src/quati").rglob("*.py")):
        code.update(path.as_posix().encode() + b"\0" + path.read_bytes())
    prompt = hashlib.sha256((REPOSITORY_ROOT / "examples/behavior/executive-secretary.yaml").read_bytes())
    return code.hexdigest(), prompt.hexdigest()


FORECAST = "weekly order volume forecast for the north region"
CALENDAR = "find my next appointment in the calendar"


def test_reg_05(tmp_path: Path) -> None:
    before = _hashes()
    harness = build(tmp_path)
    assert harness.install("forecast-lime")["data"]["lifecycle"] == "ENABLED"
    result = _new_process_search(tmp_path, FORECAST, CALENDAR)
    assert result["found"][FORECAST] == ["fixtures.forecast-lime"]
    assert result["found"][CALENDAR] == []          # negative: not installed, not found
    assert _hashes() == before


def test_reg_05_fault_restart_during_install(tmp_path: Path) -> None:
    harness = build(tmp_path)

    def crash(point: str) -> None:
        if point == "registry.before_rename":
            raise RuntimeError("injected registry restart")

    harness.store.hook = crash
    with pytest.raises(RuntimeError):
        harness.install("forecast-lime")
    result = _new_process_search(tmp_path, FORECAST)
    assert result == {"found": {FORECAST: []}, "records": 0}
