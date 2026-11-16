"""Test-only child-process runner for tests/integration/cli/test_s00_fix7_public_surface.py (LOG-0041).

Runs the public ``quati.cli.main.main`` in a fresh process. The provider configuration comes from
the ENVIRONMENT exactly as in production (``ProviderConfig.from_environment`` is not replaced); the
only test seam is that two SCRIPTED FAKE transports are registered so that the environment can
select them:

* ``scripted_fake_t04`` - ``ScriptedFakeProvider`` of ``s00_t04_support`` (no key, no endpoint);
* ``scripted_fake_keyed`` - the same scripted provider declared as needing an API key, so that the
  key reference rules and the live allowance are exercised without any vendor adapter.

Neither can make a network call. In addition every socket connection or name lookup attempted by
the process is recorded in the spy log and refused. It is never product code and never evidence of
a real provider.

Usage: ``python fix7_public_runner.py SPY_LOG SCENARIO_JSON QUATI_ARGV...`` (stdin is passed on).

``SCENARIO_JSON`` keys (all optional):

* ``script`` - list of items ``["classify"]``, ``["classify_social"]``, ``["search", query]``,
  ``["describe", capability_id]``, ``["invoke", capability_id, input]``, ``["final", text]``;
* ``umask`` - process umask (integer) set before the command runs;
* ``foreign_paths`` - paths whose owner the process must see as ANOTHER uid through ``os.stat`` and
  ``os.lstat`` on exactly that path (the technique of the independent audit's ``runner4.py``);
* ``foreign_inodes`` - paths whose owner the process must see as another uid through ``os.fstat``
  of any descriptor open on the same inode (for code that decides on a descriptor).

Real foreign ownership needs a second OS user or root; the two overrides above change only the uid
that this one process observes. They prove the refusal logic, not a real multi-user host.

Spy log lines: ``["handler", name]`` per real handler execution, ``["probe_call"]`` per provider
probe, ``["request", [tool names]]`` per non-probe model request, ``["socket", what]`` per refused
network attempt, and a last ``["script_left", n]``.
"""
import json
import os
import socket
import sys
from pathlib import Path

sys.path.insert(0, '<local-path>')

from s00_t04_support import (  # noqa: E402
    FAKE_TRANSPORT, SOCIAL, Script, ScriptedFakeProvider, classified, describe, final, invoke, search)
from quati.adapters import fixture_capabilities as fixtures  # noqa: E402
from quati.application import providers  # noqa: E402
from quati.cli import main as cli_main  # noqa: E402

LOG, SCENARIO, ARGV = sys.argv[1], json.loads(Path(sys.argv[2]).read_text(encoding='utf-8')), sys.argv[3:]
KEYED_TRANSPORT = 'scripted_fake_keyed'


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
    if kind == 'tool':
        from s00_t04_support import tool
        return tool(rest[0], **rest[1])
    if kind == 'classify_as':
        return classified(dict(SOCIAL, **rest[0]))
    if kind == 'error':
        from quati.application.providers import ProviderError
        def boom(request):
            raise ProviderError(rest[0], rest[1])
        return boom
    raise SystemExit(f'unknown script item: {kind}')


class KeyedScriptedProvider(ScriptedFakeProvider):
    """The scripted provider declared as an API-key transport (no endpoint, no network)."""
    transport = KEYED_TRANSPORT
    needs_secret = True


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
    return REAL_PROBE(self, *args, **kwargs)


fixtures.FixtureHandlerRegistry.execute = execute
ScriptedFakeProvider.probe = probe
providers.transports()
providers._REGISTRY[FAKE_TRANSPORT] = ScriptedFakeProvider
providers._REGISTRY[KEYED_TRANSPORT] = KeyedScriptedProvider
SCRIPT = Script(*[build(item) for item in SCENARIO.get('script', [])])
ScriptedFakeProvider.active_script = SCRIPT

OTHER_UID = os.getuid() + 1


class ForeignOwner:
    def __init__(self, info):
        self._info = info

    def __getattr__(self, name):
        return OTHER_UID if name == 'st_uid' else getattr(self._info, name)


FOREIGN_PATHS = {os.fspath(path) for path in SCENARIO.get('foreign_paths', [])}
FOREIGN_INODES = set()
for path in SCENARIO.get('foreign_inodes', []):
    info = os.stat(path)
    FOREIGN_INODES.add((info.st_dev, info.st_ino))

if FOREIGN_PATHS:
    def by_path(function):
        def inner(path, *args, **kwargs):
            info = function(path, *args, **kwargs)
            named = isinstance(path, (str, os.PathLike)) and os.fspath(path) in FOREIGN_PATHS
            return ForeignOwner(info) if named else info
        return inner

    os.stat, os.lstat = by_path(os.stat), by_path(os.lstat)

if FOREIGN_INODES:
    REAL_FSTAT = os.fstat

    def fstat(descriptor):
        info = REAL_FSTAT(descriptor)
        return ForeignOwner(info) if (info.st_dev, info.st_ino) in FOREIGN_INODES else info

    os.fstat = fstat

if 'umask' in SCENARIO:
    os.umask(SCENARIO['umask'])
from quati.application.ports import ProviderConfig
if SCENARIO.get('provider', 'fake') == 'fake':
    cli_main._config = lambda: ProviderConfig(transport=FAKE_TRANSPORT, allow_live=True)
elif SCENARIO.get('provider') == 'fake_nolive':
    cli_main._config = lambda: ProviderConfig(transport=FAKE_TRANSPORT, allow_live=False)
code = cli_main.main(ARGV)
for request in SCRIPT.model_requests():
    record(['request', [tool.name for tool in request.tools]])
record(['script_left', len(SCRIPT.items)])
raise SystemExit(code)
