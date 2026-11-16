"""Live blind discovery evaluations (CAP-01, CAP-02, CAP-03 L3, CAP-05).

Opt-in only: they spend real money on the operator's own provider sign-in. Set
QUATI_LIVE_EVAL=1 and optionally QUATI_EVAL_TRANSPORT / QUATI_EVAL_MODEL / QUATI_EVAL_RUNS.
Gate evidence is produced by tests/evals/run_live_eval.py (10 paraphrases x 3 runs);
these wrappers apply the same deterministic oracle from tests/evals/live_harness.py.
"""
import os
import tempfile
from pathlib import Path

import pytest

import live_harness as h

LIVE = os.environ.get('QUATI_LIVE_EVAL') == '1'
pytestmark = pytest.mark.skipif(not LIVE, reason='NOT_VERIFIED_EXTERNAL: set QUATI_LIVE_EVAL=1 to run live evals')
TRANSPORT = os.environ.get('QUATI_EVAL_TRANSPORT', 'claude_cli')
MODEL = os.environ.get('QUATI_EVAL_MODEL', 'haiku')
RUNS = int(os.environ.get('QUATI_EVAL_RUNS', '3'))
SEED = 20261116


def _base():
    return Path(tempfile.mkdtemp(prefix='quati-eval-'))


def _selection_tally(case_id):
    result = h.run_selection_case(case_id, _base(), TRANSPORT, MODEL, RUNS, SEED, workers=4)
    assert result['unauthorized_effects'] == 0
    assert result['passed'] == result['n'], result['failures']
    # CAP-02 carries the M26-AT-01 observation (`quati trace explain` with the alternatives the oracle names).
    assert result['gate_pass_with_observations'], result['observations']


def test_cap_01():
    _selection_tally('CAP-01')


def test_cap_02():
    _selection_tally('CAP-02')


def test_cap_03():
    result = h.run_disabled_case(_base(), TRANSPORT, MODEL, SEED)
    assert result['pass'], result['checks']


def test_cap_05():
    result = h.run_unprobed_case(_base(), TRANSPORT, MODEL, SEED)
    assert result['pass'], result['checks']


def test_wilson_lower_bound_of_30_of_30():
    assert round(h.wilson_lower(30, 30), 3) == 0.886
