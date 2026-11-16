from h import *
import shutil, os
P='rt1b'
def fresh():
    shutil.rmtree(A/P, ignore_errors=True); shutil.rmtree(A/(P+'-harness'), ignore_errors=True)
    q(P,'init','--json'); q(P,'capabilities','install-fixture','calendar-read','--enable-fixture','--json'); model(P,[],'models','probe','--json')
READ=[['classify'],['search','next appointment calendar'],['describe','fixtures.calendar-read'],['invoke','fixtures.calendar-read',{'limit':1}],['final','done']]
def leg(label):
    c,o,e=q(P,'doctor','--json'); pol=json.loads(o)['data']['policy']
    n0=len(spy(P)); c2,o2,e2=model(P,READ,'ask','--json','Find my next appointment'); b=brief(o2)[0]
    print(label,'| doctor exit',c,pol,'| read-ask exit',c2,b['status'],b['reason'],'| handlers',[x[1] for x in spy(P)[n0:] if x[0]=='handler'])
pol=A/P/'config/policy.json'
fresh(); real=A/'stolen-policy.json'; shutil.copy(pol,real); os.remove(pol); os.symlink(real,pol); leg('policy.json symlink')
fresh(); d=json.loads(pol.read_bytes()); d['tenant_id']='01M7JET9N7DFY50YKHHTYB8T28'; pol.write_bytes(json.dumps(d,separators=(',',':'),sort_keys=True).encode()); leg('policy wrong tenant')
fresh(); d=json.loads(pol.read_bytes()); d['rules'][0]['surprise']=True; pol.write_bytes(json.dumps(d,separators=(',',':'),sort_keys=True).encode()); leg('policy unknown rule field')
fresh(); os.remove(A/P/'config/policy.registry.json'); leg('policy registry deleted')
# attacker rewrites BOTH files consistently (no signature?): make write ALLOW and re-point the registry head
fresh(); reg=A/P/'config/policy.registry.json'; r=json.loads(reg.read_bytes()); print('registry head:',r['versions'][-1])
