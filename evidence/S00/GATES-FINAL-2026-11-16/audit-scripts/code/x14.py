import sys,os,json,glob,shutil; sys.path.insert(0,'.')
from h import *
W=[['classify'],['search','next appointment calendar'],['describe','fixtures.calendar-read'],['invoke','fixtures.calendar-read',{'limit':1}],['final','done']]
def setup():
    ready('x14'); v=json.loads(model('x14',W,'ask','Find my next appointment','--json')[1].splitlines()[0]); return v['data']['request_id']
def rp(): return [p for p in glob.glob(str(root('x14')/'data/receipts/*.json')) if json.load(open(p)).get('request_id')]
def show(rid):
    r=q('x14','trace','show',rid,'--json'); v=json.loads(r[1].splitlines()[0]); d=v['data']
    return r[0],v['status'],(v.get('error') or {}).get('code'),d.get('trace_status'),d.get('reason') or d.get('reasons') or d.get('integrity'),[u for u in v.get('uncertainties',[])][:3]
def mutate(name,f):
    rid=setup(); p=[x for x in rp() if json.load(open(x))['request_id']==rid][0]; rc=json.load(open(p)); f(rc); open(p,'w').write(json.dumps(rc)); os.chmod(p,0o600); print(name,show(rid))
print('--- original forms')
mutate('forged executed_capabilities',lambda r:r.update(executed_capabilities=r.get('executed_capabilities',[])+['fixtures.mail-search@1.0.0']))
mutate('executed_capabilities emptied',lambda r:r.update(executed_capabilities=[]))
rid=setup(); ap=root('x14')/'data/capabilities/audit.jsonl'
lines=[json.loads(l) for l in ap.read_text().splitlines()]
ev=[e for e in lines if e.get('event')=='policy.decided' and e.get('request_id',rid)==rid]
print('policy.decided lines',len(ev), list(ev[-1].keys())[:12] if ev else None)
