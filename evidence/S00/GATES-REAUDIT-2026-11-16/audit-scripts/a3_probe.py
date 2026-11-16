from h import *
import shutil
def reset(P, init=True):
    shutil.rmtree(A/P, ignore_errors=True); shutil.rmtree(A/(P+'-harness'), ignore_errors=True)
    if init: assert q(P,'init','--json')[0]==0
def run(label,P,*argv,extra=None,**sc):
    s0=len(spy(P)); f0=files(P)
    r=model3(P,[],*argv,extra=extra,**sc)
    f1=files(P)
    print(f"{label}: {one(r)} probe_calls={sum(1 for x in spy(P)[s0:] if x[0]=='probe_call')} new_files={[x for x in f1 if x not in f0 and 'harness' not in x]}")
    if 'audit3' in r[1]+r[2]: print('   PATH DISCLOSED in output:', [w for w in (r[1]+r[2]).replace('"',' ').split() if 'audit3' in w][:3])
    return r
P='pr0'; reset(P,init=False)
run('no identity: models probe',P,'models','probe','--json')
run('no identity: doctor --probe',P,'doctor','--probe','--json')
run('no identity: models probe (human)',P,'models','probe')
P='pr1'; reset(P)
run('identity + QUATI_CAPABILITY_CONTEXT=1: models probe',P,'models','probe','--json',extra={'QUATI_CAPABILITY_CONTEXT':'1'})
run('identity + QUATI_CAPABILITY_CONTEXT=1: doctor --probe',P,'doctor','--probe','--json',extra={'QUATI_CAPABILITY_CONTEXT':'1'})
run('identity + QUATI_CAPABILITY_CONTEXT=0: doctor --probe',P,'doctor','--probe','--json',extra={'QUATI_CAPABILITY_CONTEXT':'0'})
run('identity + foreign-owned data dir (uid proxy): models probe',P,'models','probe','--json',foreign_uid=True)
run('identity ok: models probe',P,'models','probe','--json')
run('identity + foreign-owned data dir AFTER dirs exist: models probe',P,'models','probe','--json',foreign_uid=True)
run('identity + foreign-owned: doctor --probe',P,'doctor','--probe','--json',foreign_uid=True)
P='pr2'; reset(P); real=A/'pr2-real'; shutil.rmtree(real,ignore_errors=True); real.mkdir(mode=0o700); 
if (A/P/'data').exists(): shutil.rmtree(A/P/'data')
os.symlink(real, A/P/'data')
run('symlinked data dir: models probe',P,'models','probe','--json'); print('   real dir content:',sorted(str(p.relative_to(real)) for p in real.rglob('*')))
run('symlinked data dir: doctor --probe',P,'doctor','--probe','--json')
run('symlinked data dir: doctor',P,'doctor','--json')
P='pr3'; reset(P); os.makedirs(A/P/'data',mode=0o700,exist_ok=True); os.makedirs(A/'pr3-fr',mode=0o700,exist_ok=True); 
os.symlink(A/'pr3-fr', A/P/'data/feature_reports')
run('symlinked feature_reports dir: models probe',P,'models','probe','--json'); print('   victim dir:',os.listdir(A/'pr3-fr'))
P='pr4'; reset(P); os.makedirs(A/P/'data',mode=0o700,exist_ok=True); os.makedirs(A/'pr4-rc',mode=0o700,exist_ok=True)
os.symlink(A/'pr4-rc', A/P/'data/receipts')
run('symlinked receipts dir: models probe',P,'models','probe','--json'); print('   victim dir:',os.listdir(A/'pr4-rc'))
# modes under umask 000
P='pr5'; reset(P,init=False)
old=os.umask(0)
q(P,'init','--json'); q(P,'capabilities','install-fixture','calendar-read','--enable-fixture','--json'); model3(P,[],'models','probe','--json'); q(P,'ask','hello','--json'); q(P,'capabilities','install',str(REPO/'examples'),'--json')
os.umask(old)
print('modes under umask 000:'); [print('  ',x) for x in files(P) if not x.startswith(('0o700 D','0o600 F'))]
print('  total entries',len(files(P)))
