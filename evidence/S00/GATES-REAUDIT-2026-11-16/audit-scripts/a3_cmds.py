from h import *
import shutil
P='cm'; shutil.rmtree(A/P, ignore_errors=True); q(P,'init','--json'); N='cm-noid'; shutil.rmtree(A/N, ignore_errors=True)
c,o,e=q(P,'--help'); print('--help exit',c); print(o[-1500:])
def row(*argv, expect=None):
    out=[]
    for prof in (P,N):
        f0=files(prof); c,o,e=q(prof,*argv,'--json')
        try: v=json.loads(o); s=f"exit {c} {v['status']} {(v.get('error') or {}).get('code')} msg={(v.get('error') or {}).get('message')!r}"[:150]; n=len(o.splitlines())
        except Exception: s=f'exit {c} NONJSON {o[:80]!r} {e[-80:]!r}'; n=len(o.splitlines())
        out.append(s+(' WROTE' if files(prof)!=f0 else '')+(f' stdout_lines={n}' if n!=1 else ''))
    print(' '.join(argv),'\n    id  :',out[0],'\n    noid:',out[1])
for argv in [('tell','c-1','text'),('status','c-1'),('inbox',),('inbox','--unread'),('inbox','--ack','m-1'),('messages',),('config','validate'),('config','validate','file.toml'),
             ('config','diff'),('config','simulate','x'),('config','propose','x'),('config','apply','x'),('config','rollback'),('worker','run'),('worker','tick'),('worker','install'),('worker','uninstall'),
             ('trace','show','t-1'),('trace','explain','t-1'),('trace','export','t-1'),('trace','replay','t-1'),('behavior','propose','x'),('behavior','simulate','x'),('behavior','diff','a','b'),('behavior','promote','x'),('behavior','rollback','x'),
             ('approvals','list'),('approve','apr-1'),('deny','apr-1','--reason','no'),('server',),('spaces','describe','s-1'),('policy','apply','f'),('config',),('trace',),('behavior',),('worker',),('bogus',),
             ('trace','show','--bogus-flag','x'),('inbox','--help')]:
    row(*argv)
# chat equivalents
c,o,e=q(P,'chat','--jsonl',stdin=b'/status c-1\n/tell c-1 hi\n/approvals\n/approve a\n/deny a no\n/help\n/bogus\n/quit\n'); print('chat exit',c); [print('   ',(lambda v:(v['status'],(v.get('error') or {}).get('code'),(v.get('error') or {}).get('message')))(json.loads(l))) for l in o.splitlines()]
# F15
P2='f15'; shutil.rmtree(A/P2, ignore_errors=True); q(P2,'init','--json')
for n in ('forecast-publish','forecast-publish','calendar-read','calendar-read'):
    c,o,e=q(P2,'capabilities','install-fixture',n,'--enable-fixture','--json'); v=json.loads(o); d=v.get('data') or {}; print('F15',n,'exit',c,v['status'],(v.get('error') or {}).get('code'),'lifecycle',d.get('lifecycle'),'reason',d.get('reason'),'already',d.get('already_installed'))
c,o,e=q(P2,'capabilities','install-fixture','mail-search','--json'); v=json.loads(o); print('F15 mail-search no enable: exit',c,v['status'],v['data'].get('lifecycle'))
c,o,e=q(P2,'capabilities','install-fixture','mail-search','--enable-fixture','--json'); v=json.loads(o); print('F15 mail-search repeat WITH enable: exit',c,v['status'],(v.get('error') or {}).get('code'),v['data'].get('lifecycle'),v['data'].get('reason'))
c,o,e=q(P2,'capabilities','install-fixture','mail-search','--json'); v=json.loads(o); print('F15 mail-search repeat no enable: exit',c,v['status'],v['data'].get('lifecycle'),v['data'].get('already_installed'))
c,o,e=q(P2,'capabilities','list','--json'); print('   list:',[(x['capability_id'],x['lifecycle']) for x in json.loads(o)['data']['capabilities']])
