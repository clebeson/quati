from h import *
import shutil, glob
P='g4cli'; T=A/'treecopy'; X={'PYTHONPATH':str(T/'src'),'PYTHONDONTWRITEBYTECODE':'1'}
shutil.rmtree(A/P, ignore_errors=True); shutil.rmtree(A/(P+'-harness'), ignore_errors=True)
assert q(P,'init','--json',extra=X)[0]==0
q(P,'capabilities','install-fixture','calendar-read','--enable-fixture','--json',extra=X)
c,o,e=model2(P,[],'models','probe','--json',extra=X); assert c==0,(o,e)
READ=[['classify'],['search','next appointment calendar'],['describe','fixtures.calendar-read'],['invoke','fixtures.calendar-read',{'limit':1}],['final','done']]
def ask(tag):
    c,o,e=model2(P,READ,'ask','--json','Find my next appointment',extra=X)
    d=json.loads(o.splitlines()[0]) if o.strip() else {}
    dig=None
    if d.get('evidence_refs'):
        r=json.loads(open(d['evidence_refs'][0].split(':',2)[2]).read()); dig=r.get('digests')
    print(tag,'exit',c,d.get('status'),(d.get('error') or {}),'| digests',{k:(dig[k][:12] if dig and dig.get(k) else None) for k in ('behavior_hash','statechart_hash','behavior_prompt_hash','behavior_build_digest')} if dig else None,'| stderr',e[-300:])
    return dig
chart=T/'examples/statecharts/commitment.yaml'; beh=T/'examples/behavior/executive-secretary.yaml'; c0=chart.read_text(); b0=beh.read_text()
d1=ask('baseline run 1:'); d2=ask('baseline run 2:'); print('  deterministic across processes:', all(d1[k]==d2[k] for k in ('behavior_hash','statechart_hash','behavior_prompt_hash','behavior_build_digest')))
import re
beh.write_text(b0.replace('max_capability_candidates: 5','max_capability_candidates: 4')); d3=ask('changed behavior (candidates 5->4):'); print('  behavior_hash changed:', d3 and d3['behavior_hash']!=d1['behavior_hash'], '| statechart same:', d3 and d3['statechart_hash']==d1['statechart_hash']); beh.write_text(b0)
chart.write_text(c0.replace('guard: authorized_request, action: commit_receipt','guard: always, action: commit_receipt')); ask('INVALID statechart (protected edge unguarded):')
c,o,e=q(P,'ask','--json','hello',extra=X); print('greeting with invalid statechart: exit',c,o[:160])
c,o,e=q(P,'doctor','--json',extra=X); print('doctor with invalid statechart: exit',c,'mentions behavior/statechart:', 'statechart' in o or 'behavior' in o)
chart.write_text(c0.replace('guard: safe_to_begin, action: start_work','guard: allow_anything, action: shell_exec')); ask('INVALID statechart (unregistered guard/action):')
chart.write_text(c0); d4=ask('restored:'); print('  restored equals baseline:', d4['statechart_hash']==d1['statechart_hash'])
