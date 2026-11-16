"""Live SOC-01 (gate protocol legs) and behavior-suite evaluations. Opt-in: QUATI_LIVE_EVAL=1 (real spend).

Gate evidence is produced by tests/evals/run_live_eval.py, which also pre-registers the run and checks
the code-digest binding; these wrappers apply the same deterministic graders.
"""
import os
import tempfile
from pathlib import Path

import pytest

import gate_harness as g
import live_harness as h

pytestmark = pytest.mark.skipif(os.environ.get('QUATI_LIVE_EVAL') != '1',
                                reason='NOT_VERIFIED_EXTERNAL: set QUATI_LIVE_EVAL=1 to run live evals')
TRANSPORT = os.environ.get('QUATI_EVAL_TRANSPORT', 'claude_cli')
MODEL = os.environ.get('QUATI_EVAL_MODEL', 'haiku')
SOC_RUNS = int(os.environ.get('QUATI_EVAL_SOC_RUNS', str(g.GATE_SOC_RUNS)))


def test_soc_01():
    result = g.run_soc01_gate(Path(tempfile.mkdtemp(prefix='quati-eval-')), TRANSPORT, MODEL, 20261116,
                              workers=4, runs=SOC_RUNS)
    assert result['pass'], (result['checks'], result['leg_status'])
    # The timeout leg has no public fault knob: it is NOT_RUN and this wrapper never reports it as run.
    assert set(result['not_run_legs']) <= {g.FAULT_LEG}, result['not_run_legs']


def test_behavior_suite():
    result = h.run_behavior_suite(Path(tempfile.mkdtemp(prefix='quati-eval-')), TRANSPORT, MODEL,
                                  os.environ.get('QUATI_EVAL_JUDGE', 'sonnet'), 20261116, workers=4)
    assert result['unauthorized_effects'] == 0
    assert result['passed'] == result['n'], result['failures']
