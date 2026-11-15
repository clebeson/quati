"""The harness blocks truthfully without credentials; this test is L1, not L3."""
import json
import os
from pathlib import Path
import subprocess
import sys


def test_missing_provider_never_becomes_passing_live_evaluation():
    env = dict(os.environ)
    for key in ['SECMA_MODEL','SECMA_BASE_URL','SECMA_ALLOW_LIVE']:
        env.pop(key,None)
    root=Path(__file__).resolve().parents[2]
    result=subprocess.run([sys.executable,str(root/'scripts/run_live_eval.py')],env=env,capture_output=True,text=True)
    assert result.returncode==3
    output=json.loads(result.stdout)
    assert output['status']=='BLOCKED' and output['actual_model_calls']==0
