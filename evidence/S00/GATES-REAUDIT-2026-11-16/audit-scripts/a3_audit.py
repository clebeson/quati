from h import *
import shutil, hashlib, stat
P='au'
READ=[['classify'],['search','next appointment calendar'],['describe','fixtures.calendar-read'],['invoke','fixtures.calendar-read',{'limit':1}],['final','done']]
def fresh():
    shutil.rmtree(A/P, ignore_errors=True); shutil.rmtree(A/(P+'-harness'), ignore_errors=True)
    assert q(P,'init','--json')[0]==0
    assert q(P,'capabilities','install-fixture','calendar-read','--enable-fixture','--json')[0]==0
    assert model3(P,[],'models','probe','--json')[0]==0
cap=A/P/'data/capabilities'; log=cap/'audit.jsonl'; victim=A/'au-victim.txt'
def reg(): return hashlib.sha256((cap/'registry.json').read_bytes()).hexdigest()[:10]
def battery(label, foreign=False):
    print('==',label, '| log lstat mode', oct(os.lstat(log).st_mode) if os.path.lexists(log) else None)
    v0=victim.read_bytes() if victim.exists() else None; r0=reg()
    kw={'foreign_uid':True} if foreign else {}
    for name,fn in [('capabilities list',lambda:model3(P,[],'capabilities','list','--json',**kw)),
                    ('capabilities search',lambda:model3(P,[],'capabilities','search','appointment','--json',**kw)),
                    ('install-fixture mail-search --enable',lambda:model3(P,[],'capabilities','install-fixture','mail-search','--enable-fixture','--json',**kw)),
                    ('disable calendar-read',lambda:model3(P,[],'capabilities','disable','fixtures.calendar-read@1.0.0','--json',**kw)),
                    ('ask scripted read',lambda:model3(P,READ,'ask','--json','Find my next appointment',**kw)),
                    ('ask greeting-only scripted',lambda:model3(P,[['classify']],'ask','--json','Hi, how are you?',**kw)),
                    ('ask hello',lambda:model3(P,[],'ask','hello','--json',**kw)),
                    ('doctor',lambda:model3(P,[],'doctor','--json',**kw))]:
        s0=len(spy(P)); r=fn()
        extra=''
        try:
            d=json.loads(r[1]); extra=f" catalog_access={None}"; 
            ref=(d.get('evidence_refs') or [None])[0]
            if ref and name.startswith('ask'):
                rec=json.loads(open(ref.split(':',2)[2]).read()); extra=f" receipt.catalog_access={rec.get('catalog_access')} catalog_digest={(rec.get('digests') or {}).get('catalog_digest') and 'set'}"
        except Exception as ex: extra=f' ({type(ex).__name__})'
        print(f"  {name}: {one(r)} handlers={[x for x in spy(P)[s0:] if x[0]=='handler']}{extra}")
    print('  victim changed:', (victim.read_bytes() if victim.exists() else None)!=v0, '| registry changed:', reg()!=r0)
fresh(); victim.write_text('VICTIM\n'); log.unlink(); os.symlink(victim, log); battery('audit.jsonl -> symlink to victim file')
fresh(); log.unlink(); os.symlink(A/'au-dangling', log); battery('audit.jsonl -> dangling symlink'); print('  dangling target created:', (A/'au-dangling').exists())
fresh(); os.link(log, A/'au-hardlink'); battery('audit.jsonl hardlinked (nlink=2)'); os.unlink(A/'au-hardlink')
fresh(); log.unlink(); os.mkfifo(log, 0o600); battery('audit.jsonl is a FIFO')
fresh(); log.unlink(); log.mkdir(); battery('audit.jsonl is a directory')
for mode in (0o644,0o640,0o604,0o400,0o000):
    fresh(); os.chmod(log, mode); battery(f'audit.jsonl mode {oct(mode)}'); print('  mode after:', oct(os.lstat(log).st_mode & 0o777))
fresh(); battery('foreign-owned (uid proxy in private_fs)', foreign=True)
fresh(); real=A/'au-realcap'; shutil.rmtree(real,ignore_errors=True); shutil.move(str(cap), str(real)); os.symlink(real, cap); battery('data/capabilities is a symlink to a private dir'); os.unlink(cap); 
fresh(); log.write_bytes(b''); battery('audit.jsonl truncated to empty (same user)')
fresh(); log.write_bytes(b'not json\n'); battery('audit.jsonl corrupted line')
