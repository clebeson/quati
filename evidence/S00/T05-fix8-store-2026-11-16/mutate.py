"""Mutation check for S00 fix round 8, store agent (LOG-0044 X1, X2, X6, X8, X11, X13, X14, X15).

Scratch copies only; the repository is never modified.

Usage: python mutate.py REPOSITORY SCRATCH_DIR [id-prefix ...]

Each mutant is applied to its own copy of ``src``, ``tests``, ``examples``, ``contracts`` and ``pyproject.toml``
and its test selection is run from that copy (child processes of the public tests import the copy, because the
tests derive the source path from their own location). A mutant is KILLED when pytest fails. A mutant without
its own selection runs the unit file; a mutant that needs the public child-process proof names it.
"""
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPOSITORY, SCRATCH = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
ONLY = sys.argv[3:]
PYTHON = REPOSITORY / '.venv' / 'bin' / 'python'
UNIT = 'tests/unit/test_s00_fix8_store.py'
PUBLIC = 'tests/integration/cli/test_s00_fix8_store_matrix.py'
TRACE = 'tests/integration/cli/test_trace_commands.py'
DEFAULT = [UNIT]
A, D, C, B = 'src/quati/application/', 'src/quati/adapters/', 'src/quati/cli/', 'src/quati/behavior/'
X1 = [PUBLIC + '::test_x1_an_unusable_packages_directory_refuses_the_install_before_any_commit']
X2 = [PUBLIC + '::test_x2_every_store_file_is_private_or_every_command_refuses_in_bounded_time', '-k',
      'registry.json and (fifo or symlink_outside) or package_manifest and (directory or mode_644) '
      'or registry.flock and mode_644 or capabilities.lock and foreign_owner']
IDN02 = ['tests/integration/test_identity.py::test_idn_02_public_cli_denies_the_read_of_a_resource_outside_the_scope']
X6 = [PUBLIC, '-k', 'x6']
X13 = [PUBLIC, '-k', 'x13 and (feature_reports or capabilities) and symlink']
X8 = [PUBLIC, '-k', 'x8']
X11 = [PUBLIC, '-k', 'x11 and (tenant_id or hard_link)']
X15 = [PUBLIC, '-k', 'x15']
X14 = [TRACE, '-k', 'partial or agrees or show_returns']
MUTANTS = [
    # --- each private-file check (adapters/private_fs.py)
    ('P01 _open: symlinks are followed', D + 'private_fs.py',
     'return os.open(path, flags | os.O_NOFOLLOW | os.O_NONBLOCK, FILE_MODE)',
     'return os.open(path, flags | os.O_NONBLOCK, FILE_MODE)'),
    ('P02 _open: blocking open (a FIFO hangs)', D + 'private_fs.py',
     'return os.open(path, flags | os.O_NOFOLLOW | os.O_NONBLOCK, FILE_MODE)',
     'return os.open(path, flags | os.O_NOFOLLOW, FILE_MODE)'),
    ('P03 _open: an unopenable path is a bare OSError, not the typed refusal', D + 'private_fs.py',
     '    except OSError:\n        raise _refuse(Path(path), "symlink or file that cannot be opened") from None',
     '    except OSError:\n        raise'),
    ('P04 _checked: no regular-file check', D + 'private_fs.py', 'if not stat.S_ISREG(info.st_mode):', 'if False:'),
    ('P05 _checked: no link-count check', D + 'private_fs.py',
     'if info.st_uid != os.getuid() or info.st_nlink != 1:', 'if info.st_uid != os.getuid():'),
    ('P06 _checked: no owner check', D + 'private_fs.py',
     'if info.st_uid != os.getuid() or info.st_nlink != 1:', 'if info.st_nlink != 1:'),
    ('P07 _wider: no mode check', D + 'private_fs.py',
     'return bool(stat.S_IMODE(info.st_mode) & 0o077)', 'return False'),
    ('P14 check_private_path: checks nothing', D + 'private_fs.py',
     '    if _wider(info, Path(path)):\n        raise _refuse(Path(path), "group or other permission bits")',
     '    return'),
    ('P15 check_private_path: a wider mode is accepted', D + 'private_fs.py',
     '    if _wider(info, Path(path)):\n        raise _refuse(Path(path), "group or other permission bits")',
     '    _wider(info, Path(path))'),
    ('P08 _verify: a writer widens a directory that lacks owner bits', D + 'private_fs.py',
     '        elif mode & DIRECTORY_MODE != DIRECTORY_MODE:\n            raise _refuse(path, "owner permission bits missing")\n',
     ''),
    ('P09 verify_entry: a directory is accepted where a store file belongs', D + 'private_fs.py',
     'if entry.name in files or not stat.S_ISDIR(os.lstat(entry).st_mode):',
     'if not stat.S_ISDIR(os.lstat(entry).st_mode):'),
    ('P10 verify_entry: only the first level is verified', D + 'private_fs.py',
     '    for name in names:\n        verify_entry(entry / name, files=files)', '    for name in names:\n        pass'),
    ('P11 verify_entry: files are not checked at all', D + 'private_fs.py',
     '            check_private_file(entry)\n            return', '            return'),
    ('P12 check_private_file: opened but not checked', D + 'private_fs.py',
     '    os.close(_checked(descriptor, Path(path), False))', '    os.close(descriptor)'),
    ('P13 open_private: descriptor not checked', D + 'private_fs.py',
     'return _checked(_open(path, flags | os.O_CREAT), Path(path), False)', 'return _open(path, flags | os.O_CREAT)'),
    # --- the registry store (adapters/capability_store.py)
    ('S01 load: plain read of registry.json (audit X2)', D + 'capability_store.py',
     'raw = None if self._verified_root(create=False) is None else read_private(self.registry_path)',
     'raw = None if self._verified_root(create=False) is None or not self.registry_path.exists() '
     'else self.registry_path.read_bytes()'),
    ('S02 lock_entries: plain read of capabilities.lock (audit X2)', D + 'capability_store.py',
     'raw = None if self._verified_root(create=False) is None else read_private(self.lock_path)',
     'raw = None if self._verified_root(create=False) is None or not self.lock_path.exists() '
     'else self.lock_path.read_bytes()'),
    ('S03 prepare: the fixed store files are not verified before the decision', D + 'capability_store.py',
     '        for name in STORE_FILES:\n            check_private_path(root / name)', '        pass'),
    ('S03p prepare: the fixed store files are not verified before the decision (public matrix)', D + 'capability_store.py',
     '        for name in STORE_FILES:\n            check_private_path(root / name)', '        pass', X2),
    ('S04 prepare: packages and staging are not verified before the decision', D + 'capability_store.py',
     '        for name in STORE_DIRECTORIES:\n            self._directory(name, create=False)\n        for name in STORE_FILES:',
     '        for name in STORE_FILES:'),
    ('S04p prepare: packages is not verified before the decision (public X1)', D + 'capability_store.py',
     '        for name in STORE_DIRECTORIES:\n            self._directory(name, create=False)\n        for name in STORE_FILES:',
     '        for name in STORE_FILES:', X1),
    ('S05 verify_packages: a package id or version may be a regular file', D + 'capability_store.py',
     '            for capability_id in sorted(os.listdir(directory)) if name == "packages" else ():\n'
     '                self._directory(name, capability_id, create=False)\n'
     '                for version in sorted(os.listdir(directory / capability_id)):\n'
     '                    self._directory(name, capability_id, version, create=False)\n', ''),
    ('S05b verify_packages: the package trees are not walked', D + 'capability_store.py',
     '            verify_entry(directory, files=frozenset({MANIFEST_FILE}))', '            pass'),
    ('S05c verify_packages: a directory is accepted in place of a manifest', D + 'capability_store.py',
     'files=frozenset({MANIFEST_FILE})', 'files=frozenset()'),
    ('S05d the stored packages are never verified before a registry read', D + 'capability_store.py',
     '            self.verify_packages()\n            self._packages_verified = True',
     '            self._packages_verified = True'),
    ('S05dp the stored packages are never verified before a registry read (public matrix)', D + 'capability_store.py',
     '            self.verify_packages()\n            self._packages_verified = True',
     '            self._packages_verified = True', X2),
    ('S05e load does not verify the stored packages first', D + 'capability_store.py',
     '        self._before_registry_use()\n        raw = None', '        raw = None'),
    ('S05f the store lock does not verify the stored packages first', D + 'capability_store.py',
     '        self._verified_root(create=True)\n        self._before_registry_use()\n',
     '        self._verified_root(create=True)\n'),
    ('S17 prepare opens the fixed files before the decision (M02 order row 7)', D + 'capability_store.py',
     '            check_private_path(root / name)', '            verify_entry(root / name)'),
    ('S17p prepare opens the fixed files before the decision (public IDN-02)', D + 'capability_store.py',
     '            check_private_path(root / name)', '            verify_entry(root / name)', IDN02),
    ('S18 the stored packages are examined before the decision (M02 order row 7)', D + 'capability_store.py',
     '            check_private_path(root / name)', '            check_private_path(root / name)\n        self.verify_packages()'),
    ('S18p the stored packages are examined before the decision (public IDN-02)', D + 'capability_store.py',
     '            check_private_path(root / name)', '            check_private_path(root / name)\n        self.verify_packages()',
     IDN02),
    ('S06 stage_package: the publish location is not verified before the commit (audit X1)', D + 'capability_store.py',
     '        self._directory("packages", *self._package_id(entries))\n', '        self._verified_root(create=True)\n'),
    ('S07 stage_package: the package id directory is not prepared before the commit', D + 'capability_store.py',
     '        return (name,) if isinstance(name, str) and name not in ("", ".", "..") and name == Path(name).name else ()',
     '        return ()'),
    ('S08 stage_package: the staging directory chain is not verified', D + 'capability_store.py',
     '        staging = self._directory("staging") / sha', '        staging = self.root / "staging" / sha'),
    ('S09 publish_package: a late failure is an untyped OSError ("no work was accepted")', D + 'capability_store.py',
     '            os.replace(staging, final)\n        except OSError as exc:\n            raise StoreChangeIncomplete() from exc',
     '            os.replace(staging, final)\n        except OSError:\n            raise'),
    ('S10 write_lock_entry: a late failure is an untyped OSError', D + 'capability_store.py',
     '            if self._change_committed:\n                raise StoreChangeIncomplete() from exc\n            raise',
     '            raise'),
    ('S11 commit point never recorded', D + 'capability_store.py',
     '            self._change_committed = self._intent_logged', '            pass'),
    ('S12 audit failure after a commit still says audit_unavailable', D + 'capability_store.py',
     'return StoreChangeIncomplete() if self._change_committed else _audit_unavailable()',
     'return _audit_unavailable()'),
    ('S13 every commit counts as a registry-service change (standalone store use mis-typed)', D + 'capability_store.py',
     '            self._change_committed = self._intent_logged',
     '            self._change_committed = True', ['tests/unit/test_s00_fix6_cli_surface.py']),
    ('S14 the store lock file is opened without the private-file check', D + 'capability_store.py',
     'os.fdopen(open_private(self.root / "registry.flock", os.O_RDWR), "a+b")',
     'os.fdopen(os.open(self.root / "registry.flock", os.O_RDWR | os.O_CREAT | os.O_NONBLOCK, 0o600), "a+b")'),
    ('S15 verify_audit checks nothing', D + 'capability_store.py',
     '        (M01 Data directory rule 4); creates and changes nothing."""\n        self.audit_events()',
     '        (M01 Data directory rule 4); creates and changes nothing."""'),
    ('S16 the write-ahead intent is never noticed', D + 'capability_store.py',
     'self._intent_logged = self._intent_logged or event.get("event") == "registry.intent"', 'pass'),
    ('S16b every audit event counts as a write-ahead intent', D + 'capability_store.py',
     'self._intent_logged = self._intent_logged or event.get("event") == "registry.intent"', 'self._intent_logged = True',
     ['tests/unit/test_s00_fix6_cli_surface.py']),
    # --- presentation of the late failure and of an unsafe file (cli/rendering.py)
    ('R01 StoreChangeIncomplete is rendered by the generic branch', C + 'rendering.py',
     '    if isinstance(exc, StoreChangeIncomplete):', '    if False:'),
    # --- the ask and probe pre-checks (application/cli_service.py, cli/main.py)
    ('C01 ask: the registry store is not verified before the model', A + 'cli_service.py',
     "        self._require_state('capabilities')\n        refused = self._admission(context)",
     "        refused = self._admission(context)"),
    ('C01p ask: the registry store is not verified before the model (public matrix)', A + 'cli_service.py',
     "        self._require_state('capabilities')\n        refused = self._admission(context)",
     "        refused = self._admission(context)", X2),
    ('C02 ask: the audit log is not verified before the model (audit X6)', A + 'cli_service.py',
     "        try:\n            self._require_state('audit_log')\n        except Refusal as exc:\n"
     "            return exc.status, exc.code, exc.reason, exc.message, ADMISSION_NEXT_ACTION\n", ''),
    # C02 on the public path is an equivalent mutant: with the port wired, the admission decision cannot be
    # logged on an unusable log, which is the same refusal with zero model calls (run recorded below).
    ('C02p ask: the audit log is not verified before the model (public; equivalent, see comment)', A + 'cli_service.py',
     "        try:\n            self._require_state('audit_log')\n        except Refusal as exc:\n"
     "            return exc.status, exc.code, exc.reason, exc.message, ADMISSION_NEXT_ACTION\n", '',
     [PUBLIC, '-k', 'x6 and torn']),
    ('C03 ask: no grant check before the model (audit X6)', A + 'cli_service.py',
     "blocked = None if self.authorize is None else self.authorize(context, 'ask_admission', 'read')",
     'blocked = None'),
    ('C03p ask: no grant check before the model (public)', A + 'cli_service.py',
     "blocked = None if self.authorize is None else self.authorize(context, 'ask_admission', 'read')",
     'blocked = None', X6),
    ('C04 ask: the admission refusal is computed but ignored', A + 'cli_service.py',
     '        if refused is not None:\n            status, code, reason, message, next_action = refused',
     '        if False:\n            status, code, reason, message, next_action = refused'),
    ('C05 ask: the FeatureReport directory is not verified (audit X13)', A + 'cli_service.py',
     "        self._require_state('feature_reports:read')\n", ''),
    ('C05p ask: the FeatureReport directory is not verified (public X13)', A + 'cli_service.py',
     "        self._require_state('feature_reports:read')\n", '', X13),
    ('C06 probe: the registry store is not verified (audit X13)', A + 'cli_service.py',
     "self._require_state('receipts', 'feature_reports', 'capabilities')", "self._require_state('receipts', 'feature_reports')"),
    ('C06p probe: the registry store is not verified (public X13)', A + 'cli_service.py',
     "self._require_state('receipts', 'feature_reports', 'capabilities')", "self._require_state('receipts', 'feature_reports')",
     X13),
    ('C08 ask: the stored packages are not verified before the model', A + 'cli_service.py',
     "        self._require_state('capability_packages')  # after the allowed decision, before any registry read\n", ''),
    ('C08p ask: the stored packages are not verified before the model (public matrix)', A + 'cli_service.py',
     "        self._require_state('capability_packages')  # after the allowed decision, before any registry read\n", '',
     X2),
    ('M05 composition guard: capability_packages checks nothing', C + 'main.py',
     '            FileRegistryStore(default_registry_root()).verify_packages()', '            pass'),
    ('C07 the admission check is made after the model path', A + 'cli_service.py',
     "        refused = self._admission(context)\n        if refused is not None:",
     "        refused = None\n        if refused is not None:"),
    ('M01 composition guard: capabilities is only a directory check', C + 'main.py',
     '            FileRegistryStore(default_registry_root()).prepare()', "            private_fs.state_directory(name)"),
    ('M01p composition guard: capabilities is only a directory check (public matrix)', C + 'main.py',
     '            FileRegistryStore(default_registry_root()).prepare()', "            private_fs.state_directory(name)",
     [PUBLIC + '::test_x2_every_store_file_is_private_or_every_command_refuses_in_bounded_time', '-k',
      'registry.json and mode_644']),
    ('M02 composition guard: audit_log checks nothing', C + 'main.py',
     '            FileRegistryStore(default_registry_root()).verify_audit()', '            pass'),
    ('M03 composition guard: a reader creates and tightens', C + 'main.py',
     "private_fs.state_directory(name.removesuffix(':read'), create=False, tighten=False)",
     "private_fs.state_directory(name.removesuffix(':read'))"),
    ('M04 the CLI answers the seed rule itself again (duplicate check)', C + 'main.py',
     '    service = _service()\n    if eval_permutation_seed is not None:',
     "    service = _service()\n    if eval_permutation_seed is not None and not synthetic_evidence:\n"
     "        _emit((2, response('DENIED', code='INVALID_INPUT', message='duplicate', next_action='duplicate')))\n"
     '    if eval_permutation_seed is not None:'),
    # --- the policy reference and the proof tier (audit X8)
    ('V01 receipt: the policy version is a constant again', A + 'cli_service.py',
     "'policy_version': self._policy_version(context),", "'policy_version': 's00-fixture-readonly/1',"),
    ('V02 receipt: the policy version is never determined', A + 'cli_service.py',
     '        return version if isinstance(version, str) else None', '        return None'),
    ('V02p receipt: the policy version is never determined (public)', A + 'cli_service.py',
     '        return version if isinstance(version, str) else None', '        return None', X8),
    ('V03 receipt: greeting and refusal claim proof tier L1 again', A + 'cli_service.py',
     "'proof_tier': None, 'provider_used': False", "'proof_tier': 'L1', 'provider_used': False"),
    ('V04 receipt: a loader failure propagates', A + 'cli_service.py',
     "        except Exception:  # noqa: BLE001 - an unreadable policy is recorded as \"not determined\", never guessed\n"
     "            return None", "        except ZeroDivisionError:\n            return None"),
    ('V05 context default: the constant that never existed is back', A + 'identity.py',
     'policy_version: str | None = None', "policy_version: str | None = 's00-fixture-readonly/1'"),
    # --- identity (audit X11)
    ('I01 a signed record with non-ULID identifiers is accepted', D + 'local_identity.py',
     'if not all(isinstance(signed.get(name), str) and ULID.fullmatch(signed[name])',
     'if not all(isinstance(signed.get(name), str) and signed[name]'),
    ('I01p a signed record with non-ULID identifiers is accepted (public)', D + 'local_identity.py',
     'if not all(isinstance(signed.get(name), str) and ULID.fullmatch(signed[name])',
     'if not all(isinstance(signed.get(name), str) and signed[name]', X11),
    ('I02 a hard-linked credential file is accepted', D + 'local_identity.py',
     '    if not directory and info.st_nlink != 1:', '    if False:'),
    ('I03 doctor does not name the hard link', D + 'runtime_facts.py',
     '    if not directory and info.st_nlink != 1:\n        return f"{label}_hard_link"\n', ''),
    # --- the asset rule (audit X15)
    ('A01 asset_root: an assets directory beside the package shadows a checkout', B + 'contracts.py',
     '    if resolved.parent.name == "src" and (checkout / "pyproject.toml").is_file() and all(', '    if False and all('),
    ('A02 asset_root: any parent with the files counts as a checkout', B + 'contracts.py',
     '    if resolved.parent.name == "src" and (checkout / "pyproject.toml").is_file() and all(',
     '    if (checkout / "pyproject.toml").is_file() and all('),
    ('A03 asset_root: pyproject.toml is not required', B + 'contracts.py',
     '    if resolved.parent.name == "src" and (checkout / "pyproject.toml").is_file() and all(',
     '    if resolved.parent.name == "src" and all('),
    ('A04 asset_root: the asset directories are not required', B + 'contracts.py',
     '            (checkout / name).is_dir() for name in ("contracts", "examples")):',
     '            True for name in ("contracts", "examples")):'),
    ('A05 asset_digest: the path is not part of the digest', B + 'contracts.py',
     'entries = sorted((path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest())',
     'entries = sorted(("", hashlib.sha256(path.read_bytes()).hexdigest())'),
    ('A06 asset_digest: the content is not part of the digest', B + 'contracts.py',
     'entries = sorted((path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest())',
     'entries = sorted((path.relative_to(root).as_posix(), "")'),
    ('A07 asset_digest: one asset group is left out', B + 'contracts.py',
     '("examples/statecharts", "*.yaml"), ("examples/policies", "*.json"))', '("examples/statecharts", "*.yaml"))'),
    ('A08 evidence writer: the asset digest is not stamped', D + 'evidence.py',
     "'code_digest': current_code_digest(), 'asset_digest': asset_digest()}}", "'code_digest': current_code_digest()}}"),
    ('A08p evidence writer: the asset digest is not stamped (public)', D + 'evidence.py',
     "'code_digest': current_code_digest(), 'asset_digest': asset_digest()}}", "'code_digest': current_code_digest()}}", X15),
    ('A09 evidence writer: a caller-supplied asset digest is kept', D + 'evidence.py',
     "return {**value, 'digests': {**(digests if isinstance(digests, dict) else {}),\n"
     "                                 'code_digest': current_code_digest(), 'asset_digest': asset_digest()}}",
     "return {**value, 'digests': {'code_digest': current_code_digest(), 'asset_digest': asset_digest(),\n"
     "                                 **(digests if isinstance(digests, dict) else {})}}"),
    ('A10 doctor: no asset digest in the behavior section', A + 'behavior_commands.py',
     '"diagnostics": [], "asset_digest": asset_digest(root)}', '"diagnostics": []}'),
    ('A10p doctor: no asset digest in the behavior section (public)', A + 'behavior_commands.py',
     '"diagnostics": [], "asset_digest": asset_digest(root)}', '"diagnostics": []}', X15),
    ('A11 trace show: the asset digest is not displayed', A + 'trace_commands.py',
     '                 "asset_digest": HEX}', '                 }', X15),
    # --- trace consistency (audit X14)
    ('T01 trace: no consistency check', A + 'trace_commands.py',
     '    notes = []\n    succeeded = shown["status"] == "SUCCEEDED"', '    return []\n    succeeded = shown["status"] == "SUCCEEDED"', X14),
    ('T02 trace: an executed capability needs no ALLOW line', A + 'trace_commands.py',
     'if not (executed | by_handler) <= allowed or not allowed', 'if not allowed', X14),
    ('T03 trace: an ALLOW line needs no invoke step', A + 'trace_commands.py',
     ' or not allowed <= {step["capability_ref"] for step in invoked}:', ':', X14),
    ('T04 trace: executed capabilities need no executing step', A + 'trace_commands.py',
     'if not executed <= by_handler or (succeeded and (', 'if (succeeded and (', X14),
    ('T05 trace: SUCCEEDED with result kind BLOCKED is accepted', A + 'trace_commands.py',
     'shown["result_kind"] == "BLOCKED" or (shown["result_kind"] == "FIXTURE_RESULT" and not executed))):',
     '(shown["result_kind"] == "FIXTURE_RESULT" and not executed))):', X14),
    ('T06 trace: FIXTURE_RESULT without an execution is accepted', A + 'trace_commands.py',
     'shown["result_kind"] == "BLOCKED" or (shown["result_kind"] == "FIXTURE_RESULT" and not executed))):',
     'shown["result_kind"] == "BLOCKED")):', X14),
    ('T07 trace: only the outcome list is compared with the ALLOW lines', A + 'trace_commands.py',
     'if not (executed | by_handler) <= allowed', 'if not executed <= allowed', X14),
]


def run(mutant):
    name, relative, old, new = mutant[:4]
    tests = mutant[4] if len(mutant) > 4 else DEFAULT
    work = SCRATCH / name.split()[0]
    shutil.rmtree(work, ignore_errors=True)
    for part in ('src', 'tests', 'examples', 'contracts'):
        shutil.copytree(REPOSITORY / part, work / part, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copy(REPOSITORY / 'pyproject.toml', work / 'pyproject.toml')
    if not name.startswith('BASELINE'):
        target = work / relative
        source = target.read_text(encoding='utf-8')
        if source.count(old) != 1:
            shutil.rmtree(work, ignore_errors=True)
            return name, f'NOT APPLIED (anchor found {source.count(old)} times)'
        target.write_text(source.replace(old, new), encoding='utf-8')
    env = {key: value for key, value in os.environ.items() if not key.startswith(('QUATI_', 'COVERAGE'))}
    env.update(PYTHONDONTWRITEBYTECODE='1')
    completed = subprocess.run([str(PYTHON), '-m', 'pytest', '-q', '-x', '-p', 'no:cacheprovider', '--tb=no', '-rf',
                                f'--basetemp={work / "tmp"}', *tests],
                               cwd=work, env=env, capture_output=True, text=True, timeout=3000)
    lines = completed.stdout.strip().splitlines()
    failures = [line for line in lines if line.startswith('FAILED')]
    failed = failures[0] if failures else ''
    verdict = 'SURVIVED' if completed.returncode == 0 else 'KILLED'
    if name.startswith('BASELINE'):
        verdict = 'PASS' if completed.returncode == 0 else 'BASELINE FAILS'
    shutil.rmtree(work, ignore_errors=True)
    return name, f'{verdict}  {failed.replace("FAILED ", "by ")[:200]}  [{lines[-1] if lines else ""}]'


if __name__ == '__main__':
    baselines = [('BASELINE-unit', '', '', ''), ('BASELINE-public-and-trace', '', '', '', [PUBLIC, TRACE]),
                 ('BASELINE-fix6-registry-idn02', '', '', '',
                  ['tests/unit/test_s00_fix6_cli_surface.py', 'tests/unit/test_s00_t03_registry.py', *IDN02])]
    selected = ([] if ONLY else baselines) + [m for m in MUTANTS if not ONLY or m[0].startswith(tuple(ONLY))]
    with ThreadPoolExecutor(max_workers=5) as pool:
        for name, verdict in pool.map(run, selected):
            print(f'{name}: {verdict}', flush=True)
