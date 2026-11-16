# S00-T01 validation and reproduction

This lane tests CLI/LOCAL identity contributions, not full SOC/IDN case closure or
S00 slice acceptance. It uses actual CLI processes, real Ed25519 signatures and
private temporary files. No live provider calls are made. The only SDK-availability
control is in the L1 configuration test; it never represents a working provider.

Install the declared dependencies in an isolated environment, for example
`python -m pip install -e '.[test]'`. Then run:

```bash
python -m pytest tests/test_reference_compiler.py tests/test_audit_regressions.py tests/test_spec_readiness.py -q
python -m pytest tests/unit/test_s00_t01.py tests/unit/test_local_identity.py tests/unit/test_cli_service.py tests/unit/test_s00_t01_review.py -q
python -m pytest tests/unit/test_execution_checkpoint.py tests/unit/test_execution_checkpoint_review.py -q
```

To measure the delivered runtime scope including real child processes, install the
coverage test dependency, then use the repository's opt-in coverage bootstrap:

```bash
export QUATI_TEST_COVERAGE_BOOTSTRAP="$PWD/tests/coverage"
export COVERAGE_PROCESS_START="$PWD/tests/coverage/s00_t01.coveragerc"
export COVERAGE_FILE="$PWD/.coverage-t01"
coverage run --rcfile="$COVERAGE_PROCESS_START" -m pytest tests/unit/test_s00_t01.py tests/unit/test_local_identity.py tests/unit/test_cli_service.py tests/unit/test_s00_t01_review.py -q
coverage combine --rcfile="$COVERAGE_PROCESS_START"
coverage report --rcfile="$COVERAGE_PROCESS_START"
```

The include list measures this delivery's five runtime modules. It does not claim
coverage of retained compiler/catalog/provider candidates. The current host has no
package-index DNS access; evidence records the actual read-only local dependency
environment used, without changing that environment or borrowing credentials.
`QUATI_TEST_COVERAGE_LIBRARY` is an optional read-only coverage library path for this
offline host; it is unnecessary when coverage is installed in the selected environment.

Broader retained-suite observations remain in the T01 receipt: the old packaged
compiler differs from reviewed sources (S00-T02), and the optional Pydantic AI SDK
is unavailable (S00-T04). No skipped or mocked test closes these obligations.
A cross-platform hashed uv lock and fresh installed-wheel qualification remain
unverified deliverables before claiming a qualified install/release.
