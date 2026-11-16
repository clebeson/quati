"""Test-only child-process runner for tests/integration/cli/test_s00_integration8_public.py (LOG-0045).

Runs the public ``quati.cli.main.main`` in a fresh process. The provider configuration comes from the
ENVIRONMENT exactly as in production; the only provider seam is the SCRIPTED FAKE transport
``scripted_fake_t04`` (``ScriptedFakeProvider`` of ``s00_t04_support``; no key, no endpoint, no
network). Every outgoing connection or name lookup attempted by the process is recorded in the spy
log and refused. It is never product code and never evidence of a real provider.

Usage: ``python integration8_runner.py SPY_LOG SCENARIO_JSON QUATI_ARGV...`` (stdin is passed on).

``SCENARIO_JSON`` keys (all optional):

* ``script`` - list of items ``["classify"]``, ``["classify_social"]``, ``["search", query]``,
  ``["describe", capability_id]``, ``["invoke", capability_id, input]``, ``["final", text]``;
* ``during_probe`` - ``[directory, outside]``: when the provider probe is called (after the command
  verified its storage and logged its authorization decision, before the measured report is stored),
  ``directory`` is renamed to ``outside`` and replaced by a symbolic link to it. This is the
  deterministic form of a path swapped between a check and its use (no timing involved);
* ``during_first_model_request`` - ``[file, outside]``: when the scripted model receives its first
  request that is not a probe (after the ask was admitted), ``file`` is renamed to ``outside`` and
  replaced by a symbolic link to it: a store file that becomes unsafe in the middle of a turn;
* ``socket_phases`` - true: the command is run three times in this one process and the three Response
  lines are printed in order: (1) as started; (2) while this process holds one REAL listening TCP
  socket bound to 127.0.0.1 port 0 and one bound socket that is NOT listening; (3) after both are
  closed. A loopback socket bound to an ephemeral port is local to this host: nothing connects to it
  and no packet leaves the machine, so it is not a network dependency.

Spy log lines: ``["handler", name]`` per real handler execution, ``["probe_call"]`` per provider
probe, ``["request", [tool names]]`` per non-probe model request, ``["socket", what]`` per refused
outgoing network attempt, and a last ``["script_left", n]``.
"""
import json
import os
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'unit'))

from s00_t04_support import (  # noqa: E402
    FAKE_TRANSPORT, SOCIAL, Script, ScriptedFakeProvider, classified, describe, final, invoke, search)
from quati.adapters import fixture_capabilities as fixtures  # noqa: E402
from quati.application import providers  # noqa: E402
from quati.cli import main as cli_main  # noqa: E402

LOG, SCENARIO, ARGV = sys.argv[1], json.loads(Path(sys.argv[2]).read_text(encoding='utf-8')), sys.argv[3:]
BUILDERS = {'classify': lambda: classified(), 'classify_social': lambda: classified(SOCIAL), 'search': search,
            'describe': describe, 'invoke': lambda capability_id, arguments: invoke(capability_id, **arguments),
            'final': final}


def record(entry):
    with open(LOG, 'a', encoding='utf-8') as log:
        log.write(json.dumps(entry, sort_keys=True) + '\n')


def refuse_network(what):
    def refused(*args, **kwargs):
        record(['socket', what])
        raise OSError(f'network use is refused in this test process ({what})')
    return refused


for name in ('connect', 'connect_ex'):
    setattr(socket.socket, name, refuse_network(name))
socket.create_connection = refuse_network('create_connection')
socket.getaddrinfo = refuse_network('getaddrinfo')

REAL_EXECUTE = fixtures.FixtureHandlerRegistry.execute
REAL_PROBE = ScriptedFakeProvider.probe


def execute(self, name, arguments, *, now):
    record(['handler', name])
    return REAL_EXECUTE(self, name, arguments, now=now)


def probe(self, *args, **kwargs):
    record(['probe_call'])
    if SCENARIO.get('during_probe'):
        directory, outside = SCENARIO['during_probe']
        os.rename(directory, outside)
        os.symlink(outside, directory, target_is_directory=True)
    return REAL_PROBE(self, *args, **kwargs)


fixtures.FixtureHandlerRegistry.execute = execute
ScriptedFakeProvider.probe = probe
providers.transports()
providers._REGISTRY[FAKE_TRANSPORT] = ScriptedFakeProvider
SCRIPT = Script(*[BUILDERS[item[0]](*item[1:]) for item in SCENARIO.get('script', [])])
ScriptedFakeProvider.active_script = SCRIPT


def swap_once(request):
    SCRIPT.before_call = None
    path, outside = SCENARIO['during_first_model_request']
    os.rename(path, outside)
    os.symlink(outside, path)


if SCENARIO.get('during_first_model_request'):
    SCRIPT.before_call = swap_once

if SCENARIO.get('socket_phases'):
    codes = [cli_main.main(ARGV)]
    listening = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listening.bind(('127.0.0.1', 0))
    listening.listen(1)
    bound_only = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    bound_only.bind(('127.0.0.1', 0))
    codes.append(cli_main.main(ARGV))
    listening.close()
    bound_only.close()
    codes.append(cli_main.main(ARGV))
    code = max(codes)
else:
    code = cli_main.main(ARGV)
for request in SCRIPT.model_requests():
    record(['request', [tool.name for tool in request.tools]])
record(['script_left', len(SCRIPT.items)])
raise SystemExit(code)
