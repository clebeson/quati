from h import *
import shutil, base64, hashlib, sys
sys.path.insert(0,str(REPO/'src'))
from quati.application.identity import canonical_bytes
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
P='az'
READ=[['classify'],['search','next appointment calendar'],['describe','fixtures.calendar-read'],['invoke','fixtures.calendar-read',{'limit':1}],['final','done']]
def fresh():
    shutil.rmtree(A/P, ignore_errors=True); shutil.rmtree(A/(P+'-harness'), ignore_errors=True)
    assert q(P,'init','--json')[0]==0
    assert q(P,'capabilities','install-fixture','calendar-read','--enable-fixture','--json')[0]==0
    assert model2(P,[],'models','probe','--json')[0]==0
def resign(mutate, sign=True):
    rp=A/P/'config/identity.json'; rec=json.loads(rp.read_text()); sig=rec.pop('signature'); mutate(rec)
    if sign:
        key=Ed25519PrivateKey.from_private_bytes((A/P/'config/device.key').read_bytes())
        sig=base64.b64encode(key.sign(canonical_bytes(rec))).decode()
    rp.write_bytes(canonical_bytes(dict(rec,signature=sig)))
def state():
    files=sorted(p for p in (A/P/'data').rglob('*') if p.is_file() and 'audit.jsonl' not in p.name and 'flock' not in p.name)
    return hashlib.sha256(b''.join(str(p).encode()+p.read_bytes() for p in files)).hexdigest()[:10], len(files)
def show(label, r, n0, st0, s0):
    c,o,e=r
    try: d=json.loads(o.splitlines()[-1]); data=d.get('data') or {}
    except Exception: print(f'  {label}: exit {c} NONJSON {o[:200]!r} {e[-200:]!r}'); return
    aud=[(a['event'],a.get('operation'),(a.get('decision') or {}).get('verdict'),(a.get('decision') or {}).get('reason_code')) for a in audit(P)[n0:]]
    st=state()
    print(f"  {label}: exit {c} {d['status']} code={(d.get('error') or {}).get('code')} reason={data.get('reason')} kind={data.get('result_kind')} wrote={'YES' if st!=st0 else 'no'} handlers={[x for x in spy(P)[s0:] if x[0]=='handler']} audit+={aud}")
    return d
def battery(label, full=False):
    print('==',label)
    cmds=[('list',lambda:q(P,'capabilities','list','--json')),
          ('search',lambda:q(P,'capabilities','search','appointment','--json')),
          ('describe',lambda:q(P,'capabilities','describe','fixtures.calendar-read','--json')),
          ('install-fixture+enable',lambda:q(P,'capabilities','install-fixture','mail-search','--enable-fixture','--json')),
          ('install-fixture unknown',lambda:q(P,'capabilities','install-fixture','nope','--json')),
          ('install path',lambda:q(P,'capabilities','install',str(REPO/'examples'),'--json')),
          ('disable',lambda:q(P,'capabilities','disable','fixtures.calendar-read@1.0.0','--json')),
          ('disable unknown',lambda:q(P,'capabilities','disable','fixtures.nope@9','--json')),
          ('ask hello',lambda:q(P,'ask','hello','--json')),
          ('ask scripted read',lambda:model2(P,READ,'ask','--json','Find my next appointment')),
          ('ask scripted greeting-only',lambda:model2(P,[['classify']],'ask','--json','Hi, how are you?')),
          ('models probe scripted',lambda:model2(P,[],'models','probe','--json')),
          ('doctor',lambda:q(P,'doctor','--json')),
          ('behavior validate',lambda:q(P,'behavior','validate','examples/behavior/package.yaml','--root',str(REPO),'--json')),
          ('config validate',lambda:q(P,'config','validate','--json'))]
    for name,fn in cmds:
        n0=len(audit(P)) if (A/P/'data/capabilities/audit.jsonl').exists() else 0; st0=state(); s0=len(spy(P))
        d=show(name,fn(),n0,st0,s0)
        if full and d and d['status']=='DENIED' and name in('list','disable'): print('    FULL:',json.dumps(d)[:600])
        if name=='ask scripted read' and d: print('    receipt catalog:', (d.get('data') or {}).get('tool_calls') and [(t['operation'],t['status'],t['reason']) for t in d['data']['tool_calls']])
import os
print(os.listdir(REPO/'examples/behavior'))
fresh(); battery('baseline OWNER (no tenant_role)')
for role in ('GUEST','MEMBER','ADMIN','guest',123,None,['OWNER'],'OWNER '):
    fresh(); resign(lambda r: r.__setitem__('tenant_role',role)); battery(f'signed tenant_role={role!r}', full=(role=='GUEST'))
fresh(); resign(lambda r: r.__setitem__('tenant_role','GUEST'), sign=False); battery('UNSIGNED hand-edit tenant_role=GUEST')
fresh(); resign(lambda r: r.__setitem__('organization_space_id',''), sign=True); battery('signed empty organization_space_id')
fresh(); resign(lambda r: r.pop('organization_space_id'), sign=True); battery('signed record missing organization_space_id')
