import json, os, subprocess, sys
from pathlib import Path
A = Path(__file__).resolve().parent
REPO = Path('<local-path>')
PY = str(REPO/'.venv/bin/python')
RUNNER = str(REPO/'tests/integration/fixtures/approval_injection_runner.py')
def env(profile, extra=None):
    root = A/profile
    e = {'PATH':'/usr/bin:/bin','HOME':str(root),'QUATI_CONFIG_DIR':str(root/'config'),'QUATI_DATA_DIR':str(root/'data'),'PYTHONPATH':str(REPO/'src')}
    e.update(extra or {}); return e
def q(profile, *argv, extra=None, stdin=None):
    c = subprocess.run([PY,'-m','quati',*argv],capture_output=True,env=env(profile,extra),input=stdin,timeout=120)
    return c.returncode, c.stdout.decode(), c.stderr.decode()
N=[0]
def model(profile, script, *argv, stdin=None, poisoned=False, extra=None):
    N[0]+=1
    h = A/(profile+'-harness'); h.mkdir(exist_ok=True)
    sc = h/f'scenario-{os.getpid()}-{N[0]}.json'; sc.write_text(json.dumps({'script':script,'poisoned_read':poisoned}))
    c = subprocess.run([PY,RUNNER,str(h/'spy.jsonl'),str(sc),*argv],capture_output=True,env=env(profile,extra),input=stdin,timeout=120)
    return c.returncode, c.stdout.decode(), c.stderr.decode()
def audit(profile):
    p = A/profile/'data/capabilities/audit.jsonl'
    return [json.loads(l) for l in p.read_text().splitlines() if l] if p.exists() else []
def spy(profile):
    p = A/(profile+'-harness')/'spy.jsonl'
    return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []
def brief(out):
    res=[]
    for l in out.splitlines():
        try: d=json.loads(l)
        except Exception: res.append(l[:200]); continue
        data=d.get('data') or {}
        res.append({'status':d['status'],'code':(d.get('error') or {}).get('code'),'kind':data.get('result_kind'),'reason':data.get('reason'),'text':data.get('text'),'tool_calls':[(t.get('operation'),t.get('status'),t.get('reason'),t.get('handler_executed')) for t in data.get('tool_calls',[])] if isinstance(data.get('tool_calls'),list) else None,'unc':d['uncertainties'][:6],'next':(d.get('next_action') or '')[:90]})
    return res
def model2(profile, script, *argv, stdin=None, extra=None, **scenario):
    N[0]+=1
    h = A/(profile+'-harness'); h.mkdir(exist_ok=True)
    sc = h/f'scenario2-{os.getpid()}-{N[0]}.json'; sc.write_text(json.dumps({'script':script,**scenario}))
    c = subprocess.run([PY,str(A/'runner2.py'),str(h/'spy.jsonl'),str(sc),*argv],capture_output=True,env=env(profile,extra),input=stdin,timeout=120)
    return c.returncode, c.stdout.decode(), c.stderr.decode()
