from h import *
import shutil
exec(open(A/'a3_probe.py').read().split("P='pr0'")[0].split('from h import *')[1])
P='pr4'; reset(P); shutil.rmtree(A/'pr4-rc',ignore_errors=True); os.makedirs(A/'pr4-rc',mode=0o700)
shutil.rmtree(A/P/'data/receipts'); os.symlink(A/'pr4-rc', A/P/'data/receipts')
run('symlinked receipts dir: models probe',P,'models','probe','--json'); print('   victim dir:',os.listdir(A/'pr4-rc'))
print('   ask hello:',one(q(P,'ask','hello','--json')))
P='pr5'; reset(P,init=False)
old=os.umask(0)
q(P,'init','--json'); q(P,'capabilities','install-fixture','calendar-read','--enable-fixture','--json'); model3(P,[],'models','probe','--json'); q(P,'ask','hello','--json'); q(P,'capabilities','install',str(REPO/'examples'),'--json')
model3(P,[['classify'],['search','next appointment calendar'],['describe','fixtures.calendar-read'],['invoke','fixtures.calendar-read',{'limit':1}],['final','done']],'ask','--json','--synthetic-evidence','Find my next appointment')
os.umask(old)
print('modes under umask 000 (non 0700 dir / 0600 file):'); [print('  ',x) for x in files(P) if not x.startswith(('0o700 D','0o600 F'))]
print('  total entries',len(files(P)))
