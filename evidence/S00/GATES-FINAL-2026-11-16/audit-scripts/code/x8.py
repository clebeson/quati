import sys,os,json; sys.path.insert(0,'.')
from h import *
W=[['classify'],['search','next appointment calendar'],['describe','fixtures.calendar-read'],['invoke','fixtures.calendar-read',{'limit':1}],['final','done']]
ready('x8')
def j(o): return json.loads(o[1].splitlines()[0])
a=j(model('x8',W,'ask','Find my next appointment','--json'))
g=j(model('x8',[['classify_social']],'ask','hello','--json'))
n=j(model('x8',[['classify'],['search','zz qq'],['invoke','NONE_FITS',{}],['final','x']],'ask','Do something exotic','--json'))
print('adopted:',open(str(root('x8')/'config/policy.registry.json')).read()[:300])
for name,v in (('work',a),('greeting',g),('nocap',n)):
    d=v['data']; rid=d['request_id']
    rc=json.loads(next((root('x8')/'data/receipts').glob(f'*{rid}*')).read_text()) if list((root('x8')/'data/receipts').glob(f'*{rid}*')) else None
    t=json.loads(q('x8','trace','show',rid,'--json')[1])
    td=t['data']
    print(name,v['status'],'receipt keys policy:',{k:x for k,x in (rc or {}).items() if 'polic' in k or 'proof' in k or 'asset' in k},'| ask.data:',{k:x for k,x in d.items() if 'polic' in k or 'proof' in k or 'asset' in k},'| trace:',t['status'],{k:x for k,x in td.items() if 'polic' in k or 'proof' in k or 'asset' in k})
