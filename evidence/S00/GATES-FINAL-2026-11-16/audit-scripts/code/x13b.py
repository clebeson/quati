import sys,os,json,stat; sys.path.insert(0,'.')
from h import *
W=[['classify'],['search','next appointment calendar'],['describe','fixtures.calendar-read'],['invoke','fixtures.calendar-read',{'limit':1}],['final','done']]
def m(p): return oct(stat.S_IMODE(os.stat(p).st_mode))
for what in ('capabilities','capabilities/packages','receipts','feature_reports','fixture_sources','capabilities/staging',''):
  for mode in (0o755,0o770,0o707,0o500):
    ready('x13b'); r=root('x13b'); p=r/'data'/what
    if not p.exists(): print(what,'absent'); break
    os.chmod(p,mode)
    res=[]
    for name,argv,sc in (('work',('ask','Find my next appointment','--json'),W),('probe',('models','probe','--json'),[]),('list',('capabilities','list','--json'),[])):
        o=model('x13b',sc,*argv); v=json.loads(o[1].splitlines()[0]); res.append((name,o[0],(v.get('data') or {}).get('reason') or v['status']))
    print(f'{what or "<data>":24} {oct(mode)} now={m(p)} ->',res,flush=True)
    os.chmod(p,0o700)
