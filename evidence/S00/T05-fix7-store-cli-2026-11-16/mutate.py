"""Mutation check for S00 fix round 7 (LOG-0041 N13/N16). Scratch copies only; the repository is never modified.

Usage: python mutate.py REPOSITORY SCRATCH_DIR [id-prefix ...]

Each mutant is applied to its own copy of ``src``, ``tests``, ``examples``, ``contracts`` and ``pyproject.toml`` and the
selected test files are run from that copy (child processes of the public tests import the copy, because
the tests derive the source path from their own location). A mutant is KILLED when pytest fails.
"""
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPOSITORY, SCRATCH = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
ONLY = sys.argv[3:]
# MUTATE_TESTS (optional, space separated) replaces the test selection; MUTATE_ALL=1 runs without -x.
PYTHON = REPOSITORY / '.venv' / 'bin' / 'python'
TESTS = ['tests/unit/test_s00_fix6_cli_surface.py', 'tests/integration/cli/test_s00_fix7_public_surface.py',
         'tests/unit/test_m17.py', 'tests/integration/cli/test_behavior_commands.py',
         'tests/integration/cli/test_trace_commands.py']
DESELECT: list = []
A, D, C = 'src/quati/application/', 'src/quati/adapters/', 'src/quati/cli/'
MUTANTS = [
    # --- the six survivors of the independent re-audit (forkT/mutate.py), on the code as it is now
    ('S1 (forkT 11j) store: state directory not verified or tightened by the store', D + 'capability_store.py',
     'return state_directory(self.root.name, root=self.root.parent, create=create)',
     'return private_directory(self.root) if create or self.root.exists() else None'),
    ('S2 (forkT 18) receipt writer: data directory not verified or tightened', D + 'evidence.py',
     "    return state_directory('receipts')",
     "    from quati.adapters.private_fs import data_root, private_directory\n"
     "    return private_directory(data_root() / 'receipts')"),
    ('S3 (forkT 11d) _checked: no S_ISREG check', D + 'private_fs.py',
     'if not stat.S_ISREG(info.st_mode):', 'if False:'),
    ('S4 (forkT 12g) key: file: branch off', A + 'providers.py', '[A-Za-z]:[\\\\/]|file:)', '[A-Za-z]:[\\\\/])'),
    # S5 (forkT 15b, package_ref) no longer exists: the equivalent mutant was a redundant path check that
    # duplicated the compiler's own containment check; the duplicate was removed in this round. The mutant
    # below removes the single remaining check instead.
    ('S5 compiler: package reference outside the root accepted (single containment check off)', 'src/quati/behavior/compiler.py',
     '    if parts.is_absolute() or ".." in parts.parts:', '    if ".." in parts.parts:'),
    # --- the key canary (N16): the auditor's leak mutant
    ('K1 (forkT 12f) key value appended to the LIVE_NOT_ALLOWED hint', A + 'providers.py',
     "issues.append(('LIVE_NOT_ALLOWED', 'QUATI_ALLOW_LIVE=1'))",
     "issues.append(('LIVE_NOT_ALLOWED', 'QUATI_ALLOW_LIVE=1 ' + str(self.environ.get(self.config.api_key_env, ''))))"),
    # --- guards added in this round
    ('G01 _verify: no owner check on the named path', D + 'private_fs.py',
     '    if os.lstat(path).st_uid != os.getuid():\n        raise _refuse(path, "foreign owner")\n    try:\n', '    try:\n'),
    ('G02 _verify: no owner check on the descriptor', D + 'private_fs.py',
     '        if info.st_uid != os.getuid():\n            raise _refuse(path, "foreign owner")\n        mode =',
     '        mode ='),
    ('G03 _verify: O_DIRECTORY dropped (a regular file accepted as a state directory)', D + 'private_fs.py',
     'os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)', 'os.O_RDONLY | os.O_NOFOLLOW)'),
    ('G04 _verify: no O_NOFOLLOW on the directory descriptor', D + 'private_fs.py',
     'os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)', 'os.O_RDONLY | os.O_DIRECTORY)'),
    ('G05 _verify: a wider mode is never tightened', D + 'private_fs.py',
     '            os.fchmod(descriptor, DIRECTORY_MODE)\n        elif mode & 0o077:', '            pass\n        elif False:'),
    ('G06 state_directory: symlinked ancestors accepted', D + 'private_fs.py',
     'if any(ancestor.is_symlink() for ancestor in current.parents):', 'if False:'),
    ('G07 state_directory: only the last component is verified', D + 'private_fs.py',
     '        private_directory(current, tighten=tighten)\n    return current',
     '        pass\n    private_directory(current, tighten=tighten)\n    return current'),
    ('G08 main: capability commands run without the directory check', C + 'main.py',
     "    commands.registry.store.prepare()\n", ''),
    ('G09 ask: no directory check after authentication', A + 'cli_service.py',
     "        self._require_state('receipts')  # LOG-0041 N1: before any read, handler or receipt\n", ''),
    ('G10 probe: no storage check before the provider call', A + 'cli_service.py',
     "        self._require_state('receipts', 'feature_reports')\n", ''),
    ('G11 probe: not authorized', A + 'cli_service.py',
     "        denied = self._authorized(context, 'models_probe', 'manage')\n", '        denied = None\n'),
    ('G12 probe: a missing authorization port allows', A + 'cli_service.py',
     '        if self.authorize is None:\n            return 4, response', '        if self.authorize is None:\n            return None\n        if False:\n            return 4, response'),
    ('G13 probe: authorized as read instead of manage', A + 'cli_service.py',
     "self._authorized(context, 'models_probe', 'manage')", "self._authorized(context, 'models_probe', 'read')"),
    ('G14 probe: a late storage failure propagates (INTERNAL_ERROR)', A + 'cli_service.py',
     '        except OSError:\n            # The directories were verified before the call',
     '        except ZeroDivisionError:\n            # The directories were verified before the call'),
    ('G15 init: no directory check before the credential is created', A + 'cli_service.py',
     "        self._require_state('receipts')  # the policy receipt must be writable before a credential is created\n", ''),
    ('G16 audit append: existing log not validated', D + 'capability_store.py',
     '            _events(raw[self._audit_verified:])\n', ''),
    ('G17 audit log: a line that is not an object accepted', D + 'capability_store.py',
     '    if not all(isinstance(event, dict) for event in events):', '    if False:'),
    ('G18 audit log: a torn last line accepted', D + 'capability_store.py',
     '    if raw and not raw.endswith(b"\\n"):', '    if False:'),
    ('G19 audit read: corrupt log is an internal error again', D + 'capability_store.py',
     '            return _events(read_private(self.audit_path) or b"")\n        except (OSError, ValueError):',
     '            return _events(read_private(self.audit_path) or b"")\n        except OSError:'),
    ('G20 exit code: a local store failure exits 5 again', C + 'rendering.py',
     "LOCAL_STORE_REASONS = ('audit_unavailable', 'audit_store_unavailable', 'state_dir_unsafe')",
     'LOCAL_STORE_REASONS = ()'),
    ('G21 main: use-case exit code not settled', C + 'main.py',
     'raise typer.Exit(settled_exit(code, value))', 'raise typer.Exit(code)'),
    ('G22 identity: a record with a missing field is accepted', C + 'main.py',
     '        if not runtime_facts.record_complete(record):\n            raise AccessDenied()\n', ''),
    ('G23 identity: a rejected credential reported as absent', A + 'cli_service.py',
     "identity.update(status='INVALID' if state['present'] else 'NOT_CONFIGURED',",
     "identity.update(status='NOT_CONFIGURED',"),
    ('G24 identity: insecure credential classified as corrupt', D + 'runtime_facts.py',
     '        if detail:\n            return state("credential_insecure", detail)\n    if len(existing)',
     '        if detail:\n            return state("credential_corrupt", detail)\n    if len(existing)'),
    ('G25 feature reports: pointer written without the directory check', D + 'feature_reports.py',
     '        state_directory(self.root.name, root=self.root.parent)\n', '        self.root.mkdir(parents=True, mode=0o700, exist_ok=True)\n'),
    ('G26 feature reports: pointer read through any directory', D + 'feature_reports.py',
     'if path is None or state_directory(self.root.name, root=self.root.parent, create=False,\n'
     '                                               tighten=False) is None:', 'if path is None:'),
    ('G27 receipt failure after a change reported as "no work was accepted"', C + 'rendering.py',
     '    if isinstance(exc, ReceiptNotWritten):', '    if False:'),
    ('G28 unsafe directory reported as an internal error', C + 'rendering.py',
     '    if isinstance(exc, UnsafeStatePath):', '    if False:'),
    ('G29 unsupported: spaces named S03', A + 'cli_service.py', "'spaces': 'S02',", "'spaces': 'S03',"),
    ('G30 main: server not registered', C + 'main.py', "for _name in ('server', 'login'):", "for _name in ('login',):"),
    ('G31 evidence: redact() returns its input', D + 'evidence.py',
     '    return clean(value)\n', '    return value\n'),
    ('G32 private_tree: files keep their mode', D + 'private_fs.py',
     '            os.close(_checked(descriptor, entry, True))', '            os.close(descriptor)'),
]


def run(mutant):
    name, relative, old, new = mutant
    work = SCRATCH / name.split()[0]
    shutil.rmtree(work, ignore_errors=True)
    for part in ('src', 'tests', 'examples', 'contracts'):
        shutil.copytree(REPOSITORY / part, work / part, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copy(REPOSITORY / 'pyproject.toml', work / 'pyproject.toml')
    if name != 'BASELINE':
        target = work / relative
        source = target.read_text(encoding='utf-8')
        if source.count(old) != 1:
            shutil.rmtree(work, ignore_errors=True)
            return name, f'NOT APPLIED (anchor found {source.count(old)} times)'
        target.write_text(source.replace(old, new), encoding='utf-8')
    env = {key: value for key, value in os.environ.items() if not key.startswith(('QUATI_', 'COVERAGE'))}
    env.update(PYTHONDONTWRITEBYTECODE='1')
    tests = os.environ.get('MUTATE_TESTS', '').split() or TESTS
    stop = [] if os.environ.get('MUTATE_ALL') else ['-x']
    completed = subprocess.run([str(PYTHON), '-m', 'pytest', '-q', *stop, '-p', 'no:cacheprovider', '--tb=no', '-rf',
                                *DESELECT, *tests],
                               cwd=work, env=env, capture_output=True, text=True, timeout=1800)
    lines = completed.stdout.strip().splitlines()
    failures = [line for line in lines if line.startswith('FAILED')]
    failed = failures[0] + (f' (+{len(failures) - 1} more)' if len(failures) > 1 else '') if failures else ''
    verdict = 'SURVIVED' if completed.returncode == 0 else 'KILLED'
    if name == 'BASELINE':
        verdict = 'PASS' if completed.returncode == 0 else 'BASELINE FAILS'
    shutil.rmtree(work, ignore_errors=True)
    return name, f'{verdict}  {failed.replace("FAILED ", "by ")[:230]}  [{lines[-1] if lines else ""}]'


if __name__ == '__main__':
    selected = [('BASELINE', '', '', '')] + [m for m in MUTANTS if not ONLY or m[0].startswith(tuple(ONLY))]
    with ThreadPoolExecutor(max_workers=6) as pool:
        for name, verdict in pool.map(run, selected):
            print(f'{name}: {verdict}', flush=True)
