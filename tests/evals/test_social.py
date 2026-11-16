"""Live SOC-01 and behavior-suite evaluations. Opt-in: QUATI_LIVE_EVAL=1 (real spend)."""
import os
import tempfile
from pathlib import Path

import pytest

import live_harness as h

pytestmark = pytest.mark.skipif(os.environ.get('QUATI_LIVE_EVAL') != '1',
                                reason='NOT_VERIFIED_EXTERNAL: set QUATI_LIVE_EVAL=1 to run live evals')
TRANSPORT = os.environ.get('QUATI_EVAL_TRANSPORT', 'claude_cli')
MODEL = os.environ.get('QUATI_EVAL_MODEL', 'haiku')


def test_soc_01():
    result = h.run_social_case(Path(tempfile.mkdtemp(prefix='quati-eval-')), TRANSPORT, MODEL, 20261116)
    assert result['pass'], [r['checks'] for r in result['results']]


def test_behavior_suite():
    result = h.run_behavior_suite(Path(tempfile.mkdtemp(prefix='quati-eval-')), TRANSPORT, MODEL,
                                  os.environ.get('QUATI_EVAL_JUDGE', 'sonnet'), 20261116, workers=4)
    assert result['unauthorized_effects'] == 0
    assert result['passed'] == result['n'], result['failures']
