from h import *
import shutil, os, hashlib
READ=[['classify'],['search','next appointment calendar'],['describe','fixtures.calendar-read'],['invoke','fixtures.calendar-read',{'limit':1}],['final','done']]
def fresh(P):
    shutil.rmtree(A/P, ignore_errors=True); shutil.rmtree(A/(P+'-harness'), ignore_errors=True)
    assert q(P,'init','--json')[0]==0
    q(P,'capabilities','install-fixture','calendar-read','--enable-fixture','--json')
    q(P,'capabilities','install-fixture','calendar-write','--enable-fixture','--json')
    c,o,e=model(P,[],'models','probe','--json'); assert c==0,(o,e)
def one(o):
    b=brief(o); return b[0] if b else None
def show(tag,c,o,e=''):
    b=one(o)
    if isinstance(b,dict): print(f'  {tag}: exit={c} status={b["status"]} code={b["code"]} kind={b["kind"]} reason={b["reason"]} calls={b["tool_calls"]} unc={b["unc"]}', ('STDERR='+e[-200:]) if e else '')
    else: print(f'  {tag}: exit={c} raw={b!r} STDERR={e[-300:]}')
def battery(P,label):
    print('==',label)
    c,o,e=q(P,'doctor','--json')
    try: d=json.loads(o)['data']; print('  doctor: exit',c,'policy=',d['policy'],'identity=',d['identity']['status'])
    except Exception: show('doctor',c,o,e)
    n0=len(spy(P)); a0=len(audit(P)) if (A/P/'data/capabilities/audit.jsonl').is_file() else 0
    c,o,e=q(P,'ask','--json','hello'); show('greeting',c,o,e)
    c,o,e=model(P,READ,'ask','--json','Find my next appointment'); show('read-ask',c,o,e)
    c,o,e=q(P,'capabilities','install-fixture','forecast-publish','--enable-fixture','--json'); b=json.loads(o) if o.strip().startswith('{') else {}; print('  enable-write: exit',c,b.get('status'),(b.get('data') or {}).get('reason'),(b.get('error') or {}).get('code'),(b.get('data') or {}).get('lifecycle'))
    c,o,e=q(P,'capabilities','search','calendar','--json'); b=json.loads(o) if o.strip().startswith('{') else {}; print('  cli-search: exit',c,b.get('status'),(b.get('error') or {}).get('code'),(b.get('data') or {}).get('reason'),[x['capability_id'] for x in (b.get('data') or {}).get('candidates',[])] if isinstance(b.get('data'),dict) else None, e[-200:])
    print('  handlers run:',[x for x in spy(P)[n0:] if x[0]=='handler'])
    try: print('  audit+:',[(x['event'],x.get('operation'),(x.get('decision') or {}).get('verdict'),(x.get('decision') or {}).get('reason_code')) for x in audit(P)[a0:]])
    except Exception as ex: print('  audit unreadable',type(ex).__name__)

P='rt'
cfg=lambda: A/P/'config'
# ---- policy legs
fresh(P); battery(P,'BASELINE')
pol=(cfg()/'policy.json'); orig=pol.read_bytes()
os.remove(pol); battery(P,'policy deleted')
fresh(P); pol.write_bytes(b'{not json'); os.chmod(pol,0o600); battery(P,'policy invalid json')
fresh(P); d=json.loads(orig if False else pol.read_bytes()); d['rules'][1]['verdict']='ALLOW'; d['rules'][1].pop('approver',None); d['rules'][1].pop('approval_ttl_seconds',None); pol.write_bytes(json.dumps(d,separators=(',',':'),sort_keys=True).encode()); battery(P,'out-of-band edit: write rule -> ALLOW')
# out-of-band edit of BOTH policy and registry head (attacker adopts by hand)
fresh(P); reg=cfg()/'policy.registry.json'; r=json.loads(reg.read_bytes()); print('registry keys',list(r), 'version keys', list(r['versions'][-1]))
fresh(P); os.chmod(pol,0o644); battery(P,'policy mode 0644')
fresh(P); real=A/'stolen-policy.json'; shutil.copy(pol,real); os.remove(pol); os.symlink(real,pol); battery(P,'policy.json is a symlink')
fresh(P); d=json.loads(pol.read_bytes()); d['tenant_id']='01M7JET9N7DFY50YKHHTYB8T28'; pol.write_bytes(json.dumps(d,separators=(',',':'),sort_keys=True).encode()); battery(P,'policy wrong tenant')
# ---- identity legs
fresh(P); os.chmod(cfg()/'identity.json',0o644); battery(P,'identity.json mode 0644')
fresh(P); os.chmod(cfg(),0o755); battery(P,'config dir mode 0755')
fresh(P); d=json.loads((cfg()/'identity.json').read_bytes()); d['personal_space_id']='01M7JET9N7EJ6004PHVEZEDQ01'; (cfg()/'identity.json').write_bytes(json.dumps(d,sort_keys=True,separators=(',',':')).encode()); battery(P,'identity space id edited (signature now invalid)')
fresh(P); shutil.move(str(cfg()),str(A/P/'config-real')); os.symlink(A/P/'config-real',cfg()); battery(P,'config dir is a symlink')
# wrong tenant: other profile's identity+policy against this data dir
fresh(P); fresh('rt-other'); shutil.rmtree(cfg()); shutil.copytree(A/'rt-other'/'config',cfg()); os.chmod(cfg(),0o700); battery(P,'config swapped with ANOTHER tenant; data dir of first tenant')
c,o,e=q(P,'capabilities','list','--json'); print('  list as other tenant:',c,o[:300])
# capability context env
fresh(P)
for cmd in (['ask','--json','hello'],['capabilities','list','--json'],['doctor','--json'],['init','--json'],['approve','apr-123','--json']):
    c,o,e=q(P,*cmd,extra={'QUATI_CAPABILITY_CONTEXT':'1'}); print('  CAPABILITY_CONTEXT',cmd[0],'exit',c,o[:160])
