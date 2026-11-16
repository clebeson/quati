"""Opt-in coverage startup for actual Quati CLI subprocesses, never product code."""
import os
import sys

if os.environ.get('COVERAGE_PROCESS_START'):
    # Optional read-only library path for the current offline validation host.
    library = os.environ.get('QUATI_TEST_COVERAGE_LIBRARY')
    if library:
        sys.path.append(library)
    import coverage
    coverage.process_startup()
