import sys,os,json,shutil; sys.path.insert(0,'.')
from h import *
W=[['classify'],['search','next appointment calendar'],['describe','fixtures.calendar-read'],['invoke','fixtures.calendar-read',{'limit':1}],['final','done']]
def brief_(o):
    try: v=json.loads(o[1].splitlines()[0]); return (o[0],v['status'],(v.get('error') or {}).get('code'),(v.get('data') or {}).get('reason'),((v.get('data') or {}).get('component') or (v.get('data') or {}).get('path')),(v.get('next_action') or '')[:70])
    except Exception: return (o[0],'??',o[1][:80],o[2][-80:])
def spies(o): return len([x for x in o[3] if x[0]=='request'])
def breakit(r,what,how):
    p=r/'data'/what
    if how=='symlink':
        t=r/'victim'; t.mkdir(exist_ok=True)
        if p.is_dir() and not p.is_symlink(): shutil.move(str(p),str(t/'moved'))
        elif p.exists(): p.unlink()
        os.symlink(t,p)
    elif how=='fifo': 
        if p.is_dir(): shutil.rmtree(p)
        else: p.unlink()
        os.mkfifo(p,0o600)
    elif how=='mode':
        os.chmod(p,0o755 if p.is_dir() else 0o644)
for what in ('feature_reports','capabilities','receipts','capabilities/packages'):
  for how in ('symlink','fifo','mode'):
    ready('x13'); r=root('x13')
    if what=='receipts' and not (r/'data/receipts').exists(): (r/'data/receipts').mkdir(mode=0o700)
    try: breakit(r,what,how)
    except Exception as e: print(what,how,'setup fail',e); continue
    print(f'## {what}:{how}')
    for name,argv,sc,stdin in (('ask work',('ask','Find my next appointment','--json'),W,None),('ask greeting',('ask','hello','--json'),[['classify_social']],None),('models probe',('models','probe','--json'),[],None),('capabilities list',('capabilities','list','--json'),[],None),('doctor',('doctor','--json'),[],None),('trace show',('trace','show','x','--json'),[],None)):
        try: o=model('x13',sc,*argv,stdin=stdin); print(f'   {name:18}',brief_(o),'requests=',spies(o),flush=True)
        except Exception as e: print(f'   {name:18} EXC {type(e).__name__}',flush=True)
