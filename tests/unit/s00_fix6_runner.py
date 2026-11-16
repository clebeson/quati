"""Test-only child-process runner for tests/unit/test_s00_fix6_authz_ask.py (audit findings F2, F3, F4).

Runs the public ``quati.cli.main.main`` in a fresh process with the SCRIPTED FAKE model provider
(``ScriptedFakeProvider`` from s00_t04_support.py) registered under a test-only transport. No
network, no vendor CLI, no credential. It is never product code and never evidence of a real
provider: the scripted model is the adversary, so every refusal observed is trusted code.

Usage: ``python s00_fix6_runner.py SPY_LOG SCENARIO_JSON QUATI_ARGV...``

``SCENARIO_JSON`` is ``{"script": [item, ...]}``. Script items: ``["classify"]`` (a work label),
``["classify_social"]`` (a social label), ``["search", query]``, ``["describe", capability_id]``,
``["invoke", capability_id, input]`` and ``["final", text]``.

The spy log gets one JSON line per real handler execution (``["handler", name]``), one per model
request that is not a probe (``["request", [offered tool names]]``) and a last line with the
number of unused script items (``["script_left", n]``).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from s00_t04_support import (  # noqa: E402
    FAKE_TRANSPORT, SOCIAL, Script, ScriptedFakeProvider, classified, describe, final, invoke, search)
from quati.adapters import fixture_capabilities as fixtures  # noqa: E402
from quati.application import providers  # noqa: E402
from quati.application.ports import ProviderConfig  # noqa: E402
from quati.cli import main as cli_main  # noqa: E402

LOG, SCENARIO, ARGV = sys.argv[1], json.loads(Path(sys.argv[2]).read_text(encoding='utf-8')), sys.argv[3:]


def record(entry):
    with open(LOG, 'a', encoding='utf-8') as log:
        log.write(json.dumps(entry, sort_keys=True) + '\n')


def build(item):
    kind, rest = item[0], item[1:]
    if kind == 'classify':
        return classified()
    if kind == 'classify_social':
        return classified(SOCIAL)
    if kind == 'search':
        return search(rest[0])
    if kind == 'describe':
        return describe(rest[0])
    if kind == 'invoke':
        return invoke(rest[0], **rest[1])
    if kind == 'final':
        return final(rest[0])
    raise SystemExit(f'unknown script item: {kind}')


REAL_EXECUTE = fixtures.FixtureHandlerRegistry.execute


def execute(self, name, arguments, *, now):
    record(['handler', name])
    return REAL_EXECUTE(self, name, arguments, now=now)


fixtures.FixtureHandlerRegistry.execute = execute
providers.transports()
providers._REGISTRY[FAKE_TRANSPORT] = ScriptedFakeProvider
SCRIPT = Script(*[build(item) for item in SCENARIO['script']])
ScriptedFakeProvider.active_script = SCRIPT
cli_main._config = lambda: ProviderConfig(transport=FAKE_TRANSPORT, allow_live=True)
code = cli_main.main(ARGV)
for request in SCRIPT.model_requests():
    record(['request', [tool.name for tool in request.tools]])
record(['script_left', len(SCRIPT.items)])
raise SystemExit(code)
