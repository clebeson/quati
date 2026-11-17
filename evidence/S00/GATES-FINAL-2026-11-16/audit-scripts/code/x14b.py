import sys,os,json,glob; sys.path.insert(0,'.')
exec(open('x14.py').read().split("rid=setup(); print")[0]) if False else None
from h import *
W=[['classify'],['search','next appointment calendar'],['describe','fixtures.calendar-read'],['invoke','fixtures.calendar-read',{'limit':1}],['final','done']]
def setup():
    ready('x14'); return json.loads(model('x14',W,'ask','Find my next appointment','--json')[1].splitlines()[0])['data']['request_id']
def show(rid):
    r=q('x14','trace','show',rid,'--json'); v=json.loads(r[1].splitlines()[0]); return r[0],v['status'],v.get('uncertainties')
def mut(name,f,audit_f=None):
    rid=setup()
    p=[x for x in glob.glob(str(root('x14')/'data/receipts/*.json')) if json.load(open(x)).get('request_id')==rid][0]
    rc=json.load(open(p)); f(rc); open(p,'w').write(json.dumps(rc)); os.chmod(p,0o600)
    if audit_f:
        ap=root('x14')/'data/capabilities/audit.jsonl'; L=[json.loads(l) for l in ap.read_text().splitlines()]; L=audit_f(L,rid); ap.write_text(''.join(json.dumps(e)+'\n' for e in L)); os.chmod(ap,0o600)
    print(f'{name:40}',show(rid),flush=True)
mut('forged outcome.executed_capabilities',lambda r:r['outcome'].update(executed_capabilities=r['outcome']['executed_capabilities']+['fixtures.mail-search@1.0.0']))
mut('executed emptied, handler ran',lambda r:r['outcome'].update(executed_capabilities=[]))
mut('outcome.status FAILED',lambda r:r['outcome'].update(status='FAILED'))
mut('outcome.result_kind GREETING',lambda r:r['outcome'].update(result_kind='GREETING'))
mut('top result_kind BLOCKED',lambda r:r.update(result_kind='BLOCKED'))
mut('policy_version forged',lambda r:r.update(policy_version='0'*64))
mut('principal_hash forged',lambda r:r.update(principal_hash='0'*64))
mut('trajectory emptied',lambda r:r.update(trajectory=[]))
mut('audit: policy.decided ALLOW removed',lambda r:None,lambda L,rid:[e for e in L if not(e.get('event')=='policy.decided' and e.get('request_id')==rid)])
def forge(L,rid):
    e=[x for x in L if x.get('event')=='policy.decided' and x.get('request_id')==rid][-1]; f=json.loads(json.dumps(e)); f['capability_id']='fixtures.mail-search'; return L+[f]
mut('audit: forged policy.decided other cap',lambda r:None,forge)
def deny(L,rid):
    for e in L:
        if e.get('event')=='policy.decided' and e.get('request_id')==rid: e['decision']=dict(e['decision'],verdict='DENY')
    return L
mut('audit: decision flipped to DENY',lambda r:None,deny)
