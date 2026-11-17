from h import *
import json, base64, os, sys
sys.path.insert(0,str(REPO/'src'))
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from quati.application.identity import canonical_bytes
def resign(P,mut):
    c=root(P)/'config'; key=Ed25519PrivateKey.from_private_bytes((c/'device.key').read_bytes())
    rec=json.loads((c/'identity.json').read_text()); rec.pop('signature'); mut(rec)
    signed=dict(rec, signature=base64.b64encode(key.sign(canonical_bytes(rec))).decode())
    (c/'identity.json').write_bytes(canonical_bytes(signed))
READ=[['classify'],['search','next appointment calendar'],['describe','fixtures.calendar-read'],['invoke','fixtures.calendar-read',{'limit':1}],['final','done']]
for role in ('MEMBER','GUEST','ADMIN',['x']):
    ready('n7'); resign('n7', lambda r: r.update(tenant_role=role))
    f0=files('n7'); a0=len(audit('n7'))
    for cmd in (('models','probe','--json'),('doctor','--probe','--json')):
        r=model('n7',[],*cmd); v=json.loads(r[1]); new=audit('n7')[a0:]; a0=len(audit('n7'))
        print(role,cmd[:2],r[0],v['status'],(v['error'] or {}).get('code'),(v['data'] or {}).get('reason'),'probe_calls',len([x for x in r[3] if x[0]=='probe_call']),'audit',[(e['event'],e.get('operation'),e['decision']['verdict'],e['decision'].get('action')) for e in new])
    r=model('n7',READ,'ask','Find my next appointment','--json'); v=json.loads(r[1]); print(role,'ask read',r[0],v['status'],v['data']['reason'],[t['reason'] for t in v['data']['tool_calls']],'handlers',len([x for x in r[3] if x[0]=='handler']),'requests',len([x for x in r[3] if x[0]=='request']))
# unauthenticated probe: no call, nothing written
fresh('n7u'); r=model('n7u',[],'models','probe','--json'); v=json.loads(r[1]); print('uninit probe',r[0],v['status'],v['error']['code'],'probe_calls',len([x for x in r[3] if x[0]=='probe_call']),'files',list(files('n7u')), os.path.exists(root('n7u')/'data'))
# live not allowed
ready('n7l'); r=model('n7l',[],'models','probe','--json',provider='fake_nolive'); v=json.loads(r[1]); print('nolive probe',r[0],v['status'],v['error']['code'],v['uncertainties'],'probe_calls',len([x for x in r[3] if x[0]=='probe_call']))
r=model('n7l',[],'doctor','--json',provider='fake_nolive'); v=json.loads(r[1]); print('doctor nolive',r[0],v['data']['provider'].get('status'),v['data']['provider'].get('measured_support'),v['data']['live_calls_allowed'])
r=model('n7l',READ,'ask','Find my next appointment','--json',provider='fake_nolive'); v=json.loads(r[1]); print('ask nolive w/ stored report',r[0],v['status'],(v['error'] or {}).get('code'),v['data']['reason'],'requests',len([x for x in r[3] if x[0]=='request']),'handlers',len([x for x in r[3] if x[0]=='handler']))
