from h import *
import shutil, hashlib
P='bh'; shutil.rmtree(A/P, ignore_errors=True); assert q(P,'init','--json')[0]==0
def bv(cmd, pkg, root, extra=None, cwd=None, profile=P):
    e=env(profile,extra)
    c=subprocess.run([PY,'-m','quati','behavior',cmd,pkg,*(['--root',str(root)] if root else []),'--json'],capture_output=True,env=e,cwd=cwd or str(A),timeout=120)
    return c.returncode,c.stdout.decode(),c.stderr.decode()
lib={}
for line in open(A/'g4.out'):
    line=line.strip()
    if ': ACCEPTED' in line or ': REJECTED' in line:
        name,verdict=line.split(': ',1)[0],('ACCEPTED' if ': ACCEPTED' in line else 'REJECTED'); lib[name]=verdict
print('library verdicts parsed:',len(lib))
mism=0; rows=[]
for d in sorted((A/'g4roots').iterdir()):
    c,o,e=bv('validate','p.yaml',d)
    try: v=json.loads(o)
    except Exception: print('NONJSON',d.name,c,o[:200],e[-200:]); mism+=1; continue
    ok=v['status']=='SUCCEEDED'
    diags=(v.get('data') or {}).get('diagnostics') or []
    haspath=all(x.get('path') for x in diags) and bool(diags)
    libv=lib.get(d.name)
    good=(ok and c==0) or ((not ok) and c==2 and (v.get('error') or {}).get('code')=='CONFIG_INVALID' and haspath)
    if libv and ((libv=='ACCEPTED')!=ok): mism+=1; print('MISMATCH lib vs cli',d.name,libv,c,v['status'])
    if not good: mism+=1; print('BAD SHAPE',d.name,c,v['status'],v.get('error'),diags[:1])
    c2,o2,e2=bv('render','p.yaml',d); v2=json.loads(o2)
    if (v2['status']=='SUCCEEDED')!=ok or c2!=c: mism+=1; print('render differs',d.name,c2,v2['status'])
    rows.append((d.name,c,v['status'],[f"{x['code']} {x['reason']} at {x['path']}" for x in diags][:2]))
print('roots:',len(rows),'accepted:',sum(1 for r in rows if r[2]=='SUCCEEDED'),'rejected exit2 CONFIG_INVALID with path:',sum(1 for r in rows if r[1]==2),'problems:',mism)
for r in rows: print('  ',r[0][:60],r[1],r[2],r[3])
