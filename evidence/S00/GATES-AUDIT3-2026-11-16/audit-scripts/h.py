import json, os, subprocess, sys, shutil
from pathlib import Path
A = Path(__file__).resolve().parent
REPO = Path('<local-path>')
PY = str(REPO/'.venv/bin/python')
RUNNER = str(A/'runner.py')
def env(profile, extra=None):
    root = A/'profiles'/profile
    e = {'PATH':'/usr/bin:/bin','HOME':str(root/'home'),'QUATI_CONFIG_DIR':str(root/'config'),'QUATI_DATA_DIR':str(root/'data'),'PYTHONPATH':str(REPO/'src'),'PYTHONDONTWRITEBYTECODE':'1'}
    e.update(extra or {}); return e
def root(profile): return A/'profiles'/profile
def fresh(profile):
    r = root(profile)
    if r.exists(): shutil.rmtree(r)
    h = A/'profiles'/(profile+'-harness')
    if h.exists(): shutil.rmtree(h)
    r.mkdir(parents=True); return r
def q(profile, *argv, extra=None, stdin=None, cwd=None):
    c = subprocess.run([PY,'-m','quati',*argv],capture_output=True,env=env(profile,extra),input=stdin,timeout=120,cwd=cwd or str(A))
    return c.returncode, c.stdout.decode(), c.stderr.decode()
N=[0]
def model(profile, script, *argv, stdin=None, extra=None, **scenario):
    N[0]+=1
    h = A/'profiles'/(profile+'-harness'); h.mkdir(parents=True, exist_ok=True)
    sc = h/f'scenario-{os.getpid()}-{N[0]}.json'; sc.write_text(json.dumps({'script':script, **scenario}))
    spy = h/f'spy-{os.getpid()}-{N[0]}.jsonl'
    c = subprocess.run([PY,RUNNER,str(spy),str(sc),*argv],capture_output=True,env=env(profile,extra),input=stdin,timeout=25,cwd=str(A))
    sp = [json.loads(l) for l in spy.read_text().splitlines()] if spy.exists() else []
    return c.returncode, c.stdout.decode(), c.stderr.decode(), sp
def ready(profile, fixtures=('calendar-read',)):
    fresh(profile)
    assert q(profile,'init','--json')[0]==0
    for f in fixtures:
        r=q(profile,'capabilities','install-fixture',f,'--enable-fixture','--json'); assert r[0]==0, r
    r = model(profile, [], 'models','probe','--json'); assert r[0]==0, r
def audit(profile):
    p = root(profile)/'data/capabilities/audit.jsonl'
    return [json.loads(l) for l in p.read_text().splitlines() if l] if p.exists() else []
def files(profile):
    r=root(profile); out={}
    for base in (r/'config', r/'data'):
        if base.exists() and not base.is_symlink():
            for p in sorted(base.rglob('*')):
                if p.is_file() and not p.is_symlink(): out[str(p.relative_to(r))]=p.read_bytes()
    return out
def brief(out):
    res=[]
    for l in out.splitlines():
        try: d=json.loads(l)
        except Exception: res.append(l[:200]); continue
        data=d.get('data') or {}
        res.append({'status':d['status'],'code':(d.get('error') or {}).get('code'),'kind':data.get('result_kind'),'reason':data.get('reason'),'text':data.get('text'),'launched':data.get('launched'),'pu':data.get('provider_used'),'tc':[(t.get('operation'),t.get('status'),t.get('reason'),t.get('handler_executed')) for t in data.get('tool_calls',[])] if isinstance(data.get('tool_calls'),list) else None})
    return res
