from h import *
import shutil, hashlib
def model4(profile, script, *argv, **scenario):
    h = A/(profile+'-harness'); h.mkdir(exist_ok=True); sc=h/'sc4.json'; sc.write_text(json.dumps({'script':script,**scenario}))
    c = subprocess.run([PY,str(A/'runner4.py'),str(h/'spy.jsonl'),str(sc),*argv],capture_output=True,env=env(profile),timeout=120)
    return c.returncode, c.stdout.decode(), c.stderr.decode()
READ=[['classify'],['search','next appointment calendar'],['describe','fixtures.calendar-read'],['invoke','fixtures.calendar-read',{'limit':1}],['final','done']]
P='fo'; shutil.rmtree(A/P, ignore_errors=True); shutil.rmtree(A/(P+'-harness'), ignore_errors=True)
q(P,'init','--json'); q(P,'capabilities','install-fixture','calendar-read','--enable-fixture','--json'); model2(P,[],'models','probe','--json')
D=str(A/P/'data')
def lc(): return [(x['capability_id'],x['lifecycle']) for x in json.loads(q(P,'capabilities','list','--json')[1])['data']['capabilities']]
print('before:',lc(), 'audit events',len(audit(P)))
for name,argv,script in [('capabilities list',('capabilities','list','--json'),[]),('install-fixture mail-search --enable-fixture',('capabilities','install-fixture','mail-search','--enable-fixture','--json'),[]),
                  ('disable calendar-read',('capabilities','disable','fixtures.calendar-read@1.0.0','--json'),[]),('ask scripted read',('ask','--json','Find my next appointment'),READ),('models probe',('models','probe','--json'),[])]:
    n0=len(audit(P)); s0=len(spy(P)); r=model4(P,script,*argv,foreign_path=D)
    print(f"  data dir reported foreign-owned (uid 0) -> {name}: {one(r)} audit+={[a['event'] for a in audit(P)[n0:]]} handlers={[x for x in spy(P)[s0:] if x[0]=='handler']}")
print('after :',lc())
# real symlinked data dir
P='fs'; shutil.rmtree(A/P, ignore_errors=True); shutil.rmtree(A/'fs-real', ignore_errors=True); q(P,'init','--json'); shutil.move(str(A/P/'data'),str(A/'fs-real')); os.symlink(A/'fs-real',A/P/'data')
for argv in (('capabilities','list','--json'),('capabilities','install-fixture','mail-search','--enable-fixture','--json'),('capabilities','list','--json'),('ask','hello','--json')):
    print('  data dir is a symlink ->',' '.join(argv[:3]),':',one(q(P,*argv)))
print('   registry under symlink target:', sorted(str(p.relative_to(A/'fs-real')) for p in (A/'fs-real').rglob('registry.json')), 'audit lines', len((A/'fs-real/capabilities/audit.jsonl').read_text().splitlines()) if (A/'fs-real/capabilities/audit.jsonl').exists() else None)
