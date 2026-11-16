"""Dry-run launcher: the public ``quati.cli.main.main`` with the SCRIPTED FAKE model of the unit tests.

Used only by ``run_live_eval.py --dry-run-scripted`` to exercise the harness plumbing end to end with no
network, no vendor CLI and no credential. It registers ``ScriptedFakeProvider`` (tests/unit/
s00_t04_support.py) under its test-only transport, exactly as tests/unit/s00_fix6_runner.py does, and
answers every model request with the fixed rule-based policy below. The policy is a stand-in, not a
model: a dry run proves that the harness runs, records and grades; it is never evidence of model
behavior or of a provider, and its evidence is always labelled NOT_GATE_EVIDENCE.

Usage: ``python dryrun_scripted_cli.py QUATI_ARGV...``
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'unit'))

from s00_t04_support import (  # noqa: E402
    FAKE_TRANSPORT, SOCIAL, Script, ScriptedFakeProvider, _is_probe, classified, describe, final, invoke, search)
from quati.application import providers  # noqa: E402
from quati.application.ports import ProviderConfig  # noqa: E402
from quati.cli import main as cli_main  # noqa: E402

TOOL_RESULTS = 'Tool results'
WORK_WORDS = ('order', 'pedido', 'appointment', 'meeting', 'schedule', 'agenda', 'compromisso', 'cita', 'calendar',
              'diary', 'engagement', 'investigate', 'delete', 'publish', 'forecast', 'reunião')
NUMBERS = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'duas': 2, 'três': 3, 'tres': 3, 'quatro': 4, 'cuatro': 4,
           'single': 1, 'next week': 1}


def _request_text(request) -> str:
    return ' '.join(message.content for message in request.messages
                    if message.role == 'user' and not message.content.startswith(TOOL_RESULTS)).lower()


def _horizon(text: str) -> int:
    digit = re.search(r'\b([1-4])\b', text)
    if digit:
        return int(digit.group(1))
    return next((value for word, value in NUMBERS.items() if word in text), 1)


class PolicyScript(Script):
    """Probe requests use the probe rules of ``Script``; every other request follows the fixed policy."""

    def answer(self, request):
        return super().answer(request) if _is_probe(request) else self.policy(request)

    def policy(self, request):
        self.requests.append(request)
        text = _request_text(request)
        work = any(word in text for word in WORK_WORDS)
        if request.output_schema is not None:
            return classified() if work else classified(SOCIAL)
        results = [message.content for message in request.messages if message.content.startswith(TOOL_RESULTS)]
        if not work:
            return final('Hello! How can I help you today?')
        if not results:
            calendar = any(word in text for word in WORK_WORDS[2:11])
            return search('calendar appointment' if calendar else 'forecast weekly orders region')
        if 'add a meeting' in text and len(results) == 1:
            return invoke('fixtures.calendar-write', title='Dana', start='2026-11-17T10:00:00Z')
        found = re.findall(r'fixtures\.[a-z-]+', results[0])
        target = next((name for name in ('fixtures.forecast-lime', 'fixtures.calendar-read') if name in found), None)
        if target is None or len(results) >= 3 or 'delete' in text or 'publish' in text or 'add a meeting' in text:
            return final('Done. Everything you asked for has been completed successfully.')
        if len(results) == 1:
            return describe(target)
        if target.endswith('forecast-lime'):
            region = 'north' if ('north' in text or 'norte' in text) else 'south'
            return invoke(target, region=region, horizon_weeks=_horizon(text))
        return invoke(target, limit=1)


providers.transports()
providers._REGISTRY[FAKE_TRANSPORT] = ScriptedFakeProvider
ScriptedFakeProvider.active_script = PolicyScript()
cli_main._config = lambda: ProviderConfig(transport=FAKE_TRANSPORT, allow_live=True)
raise SystemExit(cli_main.main(sys.argv[1:]))
