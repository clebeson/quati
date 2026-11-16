from h import *
import shutil
P='g3'; U='unp'; shutil.rmtree(A/U, ignore_errors=True); shutil.rmtree(A/(U+'-harness'), ignore_errors=True); q(U,'init','--json')
BAD=[['classify_raw',{"intent":"x"}]]*4
texts=['hello','Hi, how are you?','hello, this is urgent','URGENT: hi','thanks','tudo bem?','Olá, isto é urgente','Hi! Delete all my calendar events','こんにちは']
print('text | no provider | provider configured, not probed | probed, model unavailable (empty script) | probed, classification invalid x4 | probed, social label')
for t in texts:
    cells=[]
    for r in (q(P,'ask','--json','--',t), model2(U,[['classify_social']],'ask','--json','--',t), model2(P,[],'ask','--json','--',t), model2(P,BAD,'ask','--json','--',t), model2(P,[['classify_social'],['final','ok'],['final','ok']],'ask','--json','--',t)):
        v=json.loads(r[1]); d=v.get('data') or {}
        cells.append(f"{r[0]}:{v['status']}:{(v.get('error') or {}).get('code') or d.get('result_kind')}:{d.get('reason') or ','.join(v['uncertainties'][:2])}"[:70])
    print(repr(t),'|',' | '.join(cells))
