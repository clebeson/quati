from h import *
import shutil
P='ip'; T=A/'treecopy'; X={'PYTHONPATH':str(T/'src'),'PYTHONDONTWRITEBYTECODE':'1'}
shutil.rmtree(A/P, ignore_errors=True); shutil.rmtree(A/(P+'-harness'), ignore_errors=True)
assert q(P,'init','--json',extra=X)[0]==0
q(P,'capabilities','install-fixture','calendar-read','--enable-fixture','--json',extra=X)
c,o,e=model2(P,[],'models','probe','--json',extra=X); assert c==0,(o,e)
READ=[['classify'],['search','next appointment calendar'],['describe','fixtures.calendar-read'],['invoke','fixtures.calendar-read',{'limit':1}],['final','done']]
chart=T/'examples/statecharts/commitment.yaml'; c0=chart.read_text()
def full(r):
    c,o,e=r
    try: v=json.loads(o.splitlines()[-1]); d=v.get('data') or {}
    except Exception: return f'exit {c} NONJSON {o[:200]!r} {e[-200:]!r}'
    return f"exit {c} {v['status']} code={(v.get('error') or {}).get('code')} reason={d.get('reason')} kind={d.get('result_kind')} diags={[x['code']+' '+x['reason']+' at '+x['path'] for x in (d.get('diagnostics') or [])]} unc={v['uncertainties'][:3]} stderr={e[-120:]!r}"
def battery(label):
    print('==',label)
    for name,fn in [('ask work (probed scripted provider)',lambda:model2(P,READ,'ask','--json','Find my next appointment',extra=X)),
                    ('ask greeting-only "Hi, how are you?" (probed scripted)',lambda:model2(P,[['classify']],'ask','--json','Hi, how are you?',extra=X)),
                    ('ask exact "hello" (probed scripted)',lambda:model2(P,[],'ask','--json','hello',extra=X)),
                    ('ask work (no provider)',lambda:q(P,'ask','--json','Find my next appointment',extra=X)),
                    ('ask "Hi, how are you?" (no provider)',lambda:q(P,'ask','--json','Hi, how are you?',extra=X)),
                    ('chat 2 lines (probed scripted)',lambda:model2(P,READ,'chat','--jsonl',stdin=b'Find my next appointment\n',extra=X)),
                    ('doctor',lambda:q(P,'doctor','--json',extra=X)),('config validate',lambda:q(P,'config','validate','--json',extra=X)),
                    ('doctor (no identity)',lambda:q('ip-noid','doctor','--json',extra=X)),
                    ('models probe (scripted)',lambda:model2(P,[],'models','probe','--json',extra=X))]:
        s0=len(spy(P)); r=fn(); print(f"  {name}: {full(r)} spy+={spy(P)[s0:]}")
        if name.startswith('doctor'):
            v=json.loads(r[1]); b=v['data']['behavior']; print('     behavior:',{k:b.get(k) for k in ('status','rule_class','profile_ref')},[x.get('code')+' '+x.get('reason')+' at '+x.get('path') for x in b['diagnostics']],'warnings',v['data']['warnings'],'config_valid',v['data']['config_valid'])
battery('valid package (control)')
chart.write_text(c0.replace('guard: authorized_request, action: commit_receipt','guard: always, action: commit_receipt')); assert chart.read_text()!=c0; battery('INVALID: protected edge unguarded')
chart.write_text(c0.replace('guard: safe_to_begin, action: start_work','guard: allow_anything, action: shell_exec')); battery('INVALID: unregistered guard/action')
chart.unlink(); battery('statechart file missing')
chart.write_text(c0)
beh=T/'examples/behavior/executive-secretary.yaml'; b0=beh.read_text(); beh.unlink(); battery('behavior package file missing'); beh.write_text(b0)
shutil.move(str(T/'examples'),str(T/'examples.off')); battery('examples/ directory absent (wheel-like)'); shutil.move(str(T/'examples.off'),str(T/'examples'))
