"""Single-point mutants of the integration-step source changes, run on a scratch copy of the repository.

Usage: python mutate.py REPOSITORY SCRATCH_COPY. Each mutant must be killed by the named tests.
"""
import shutil
import subprocess
import sys
from pathlib import Path

REPO, COPY = Path(sys.argv[1]), Path(sys.argv[2])
UNIT = 'tests/unit/test_s00_integration7.py'
PUBLIC = 'tests/integration/cli/test_s00_integration7_public.py'
MUTANTS = [
    ('A sink does not stamp the code digest', 'src/quati/adapters/evidence.py',
     "    record = redact({**bound_to_code(value), 'timestamp'", "    record = redact({**value, 'timestamp'", [UNIT, PUBLIC]),
    ('A caller may choose the code digest', 'src/quati/adapters/evidence.py',
     "    return {**value, 'digests': {**(digests if isinstance(digests, dict) else {}),\n"
     "                                 'code_digest': current_code_digest()}}",
     "    return {**value, 'digests': {'code_digest': current_code_digest(),\n"
     "                                 **(digests if isinstance(digests, dict) else {})}}", [UNIT]),
    ('B1 fixture tree keeps the umask modes', 'src/quati/adapters/fixture_capabilities.py',
     "    return private_tree(write_package(Path(sources_dir) / name, FIXTURE_MANIFESTS[name]))",
     "    return write_package(Path(sources_dir) / name, FIXTURE_MANIFESTS[name])",
     ['tests/integration/cli/test_s00_fix7_public_surface.py']),
    ('B2 identifiers are not validated', 'src/quati/adapters/local_identity.py',
     "            if not all(isinstance(signed.get(name), str) and signed[name] for name in IDENTIFIER_FIELDS):",
     "            if False:", [UNIT]),
    ('B2 an empty identifier is accepted', 'src/quati/adapters/local_identity.py',
     "            if not all(isinstance(signed.get(name), str) and signed[name] for name in IDENTIFIER_FIELDS):",
     "            if not all(isinstance(signed.get(name), str) for name in IDENTIFIER_FIELDS):", [UNIT]),
    ('B3 authorizer ignores the injected clock', 'src/quati/cli/composition.py',
     "        discovery = _parts(identity, context, clock=clock, ids=ids, handlers=None)[2]",
     "        discovery = _parts(identity, context, clock=system_clock, ids=ids, handlers=None)[2]", [UNIT]),
    ('B4 capability use case exits 5 for a local store', 'src/quati/application/capability_commands.py',
     "        return settled_exit(5, value)       # 4 when the reason is a local store (M01 exit table row 4)",
     "        return 5", [UNIT, 'tests/integration/test_identity.py']),
    ('B4 ask use case exits 5 for a local store', 'src/quati/application/ask.py',
     '        code = settled_exit(exit_code(value["status"], (value["error"] or {}).get("code")), value)',
     '        code = exit_code(value["status"], (value["error"] or {}).get("code"))', [UNIT]),
    ('B4 a reason is dropped from the shared list', 'src/quati/domain/diagnostics.py',
     'LOCAL_STORE_REASONS = ("audit_unavailable", "audit_store_unavailable", "state_dir_unsafe")',
     'LOCAL_STORE_REASONS = ("audit_unavailable", "audit_store_unavailable")', [UNIT]),
    ('B5 result_kind is not recorded', 'src/quati/application/cli_service.py',
     "                  'status': result['status'], 'result_kind': result['data'].get('result_kind'),",
     "                  'status': result['status'],", [PUBLIC]),
    ('B5 trace falls back to the record kind when the outcome kind is malformed',
     'src/quati/application/trace_commands.py',
     '                        if isinstance(record.get("outcome"), dict)\n',
     '                        or True if isinstance(record.get("outcome"), dict)\n',
     ['tests/integration/cli/test_trace_commands.py']),
    ('B5 trace ignores the record kind', 'src/quati/application/trace_commands.py',
     '                        else copy.take(record, "result_kind", _one_of(*RESULT_KINDS), "result_kind")),',
     '                        else None),', [PUBLIC]),
    ('B6 ask does not verify the capabilities directory', 'src/quati/application/cli_service.py',
     "        self._require_state('capabilities')\n", "", [PUBLIC]),
    ('D packaged assets are never used', 'src/quati/behavior/contracts.py',
     "    return packaged if packaged.is_dir() else Path(package).resolve().parents[1]",
     "    return Path(package).resolve().parents[1]", [UNIT, PUBLIC]),
    ('D a missing contract schema is an unhandled error', 'src/quati/behavior/contracts.py',
     "            except OSError:\n", "            except KeyError:\n", [UNIT, PUBLIC]),
    ('D the missing-schema diagnostic leaks the directory', 'src/quati/behavior/contracts.py',
     'ErrorCode.NOT_FOUND, f"contracts/{schema_name}", "CONTRACT_NOT_FOUND",',
     'ErrorCode.NOT_FOUND, f"{self.contracts_dir}/{schema_name}", "CONTRACT_NOT_FOUND",', [UNIT]),
]

killed = 0
for label, path, old, new, tests in MUTANTS:
    target = COPY / path
    original = (REPO / path).read_text(encoding='utf-8')
    assert original.count(old) == 1, (label, original.count(old))
    target.write_text(original.replace(old, new), encoding='utf-8')
    try:
        done = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '-x', *tests], cwd=COPY,
                              capture_output=True, text=True, timeout=900)
    finally:
        target.write_text(original, encoding='utf-8')
    failed = next((line for line in done.stdout.splitlines() if line.startswith('FAILED')), None)
    verdict = 'KILLED' if done.returncode == 1 and failed else f'SURVIVED (exit {done.returncode})'
    killed += verdict == 'KILLED'
    print(f'{verdict:9} {label} :: {path} :: {(failed or done.stdout.strip().splitlines()[-1])[:150]}', flush=True)
print(f'{killed} of {len(MUTANTS)} mutants killed')
