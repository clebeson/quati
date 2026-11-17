from h import *
import json, os, shutil, stat, subprocess, sys, hashlib, time
P='m2'; ROOT=root(P); TPL=A/'profiles'/'m2-template'; VICT=A/'profiles'/'m2-victim'
READ=[['classify'],['search','next appointment calendar'],['describe','fixtures.calendar-read'],['invoke','fixtures.calendar-read',{'limit':1}],['final','done']]
if TPL.exists(): shutil.rmtree(TPL)
ready(P)
r=model(P,READ,'ask','Find my next appointment','--json'); assert r[0]==0
RID=json.loads(r[1])['data']['request_id']
r=q(P,'capabilities','install-fixture','mail-search','--json')   # creates fixture_sources
shutil.copytree(ROOT,TPL,symlinks=True)
def restore():
    subprocess.run(['chmod','-R','u+rwx',str(ROOT)],capture_output=True)
    shutil.rmtree(ROOT); shutil.copytree(TPL,ROOT,symlinks=True)
    if VICT.exists():
        subprocess.run(['chmod','-R','u+rwx',str(VICT)],capture_output=True); shutil.rmtree(VICT)
    VICT.mkdir()
def snap(base):
    out={}
    for dp,dn,fn in os.walk(base, followlinks=False):
        for n in dn+fn:
            p=os.path.join(dp,n); st=os.lstat(p)
            if stat.S_ISLNK(st.st_mode): out[p]=('L',os.readlink(p))
            elif stat.S_ISREG(st.st_mode):
                try: out[p]=('F',hashlib.sha256(open(p,'rb').read()).hexdigest(),stat.S_IMODE(st.st_mode))
                except OSError: out[p]=('F?',)
            elif stat.S_ISDIR(st.st_mode): out[p]=('D',stat.S_IMODE(st.st_mode))
            else: out[p]=('X',)
    return out
CMDS={
 'greet':([], ('ask','hello','--json')),
 'work':(READ, ('ask','Find my next appointment','--json')),
 'chat-work':(READ, ('chat','--jsonl')),
 'list':([], ('capabilities','list','--json')),
 'search':([], ('capabilities','search','calendar','--json')),
 'describe':([], ('capabilities','describe','fixtures.calendar-read','--json')),
 'install':([], ('capabilities','install-fixture','forecast-quick','--enable-fixture','--json')),
 'disable':([], ('capabilities','disable','fixtures.calendar-read@1.0.0','--json')),
 'probe':([], ('models','probe','--json')),
 'doctor-probe':([], ('doctor','--probe','--json')),
 'doctor':([], ('doctor','--json')),
 'trace-show':([], ('trace','show',RID,'--json')),
 'trace-explain':([], ('trace','explain',RID,'--json')),
}
D=ROOT/'data'
def mk_symlink_dir(p):
    t=VICT/p.name; shutil.move(str(p),str(t)); os.symlink(t,p)
def mk_file(p):
    if p.is_dir(): shutil.rmtree(p)
    p.write_text('x')
def mk_mode(p,m): os.chmod(p,m)
def f_symlink(p):
    t=VICT/p.name
    if p.exists(): shutil.move(str(p),str(t))
    else: t.write_bytes(b'')
    os.symlink(t,p)
def f_fifo(p):
    if p.exists(): os.unlink(p)
    os.mkfifo(p,0o600)
def f_hard(p):
    if not p.exists(): p.write_bytes(b''); os.chmod(p,0o600)
    os.link(p,VICT/(p.name+'.hard'))
def f_mode(p):
    if not p.exists(): p.write_bytes(b'')
    os.chmod(p,0o644)
cases=[]
for d in ('', 'capabilities','receipts','feature_reports','fixture_sources','capabilities/packages'):
    p=D/d if d else D
    cases += [(f'dir:{d or "data"}:symlink', lambda p=p: mk_symlink_dir(p), {}),
              (f'dir:{d or "data"}:foreign', lambda: None, {'foreign_paths':[str(p)],'foreign_inodes':[str(p)]}),
              (f'dir:{d or "data"}:mode0755', lambda p=p: mk_mode(p,0o755), {}),
              (f'dir:{d or "data"}:mode0500', lambda p=p: mk_mode(p,0o500), {})]
    if d: cases.append((f'dir:{d}:is-file', lambda p=p: mk_file(p), {}))
receipt=sorted((TPL/'data'/'receipts').glob('*.json'))[0].name
fr=sorted((TPL/'data'/'feature_reports').glob('*.json'))[0].name
for f in ('capabilities/audit.jsonl','capabilities/registry.json','capabilities/registry.flock','capabilities/capabilities.lock','receipts/'+receipt,'feature_reports/'+fr):
    p=D/f
    cases += [(f'file:{f.split("/")[0]}/{p.name[:14]}:symlink', lambda p=p: f_symlink(p), {}),
              (f'file:{f.split("/")[0]}/{p.name[:14]}:fifo', lambda p=p: f_fifo(p), {}),
              (f'file:{f.split("/")[0]}/{p.name[:14]}:hardlink', lambda p=p: f_hard(p), {}),
              (f'file:{f.split("/")[0]}/{p.name[:14]}:mode0644', lambda p=p: f_mode(p), {}),
              (f'file:{f.split("/")[0]}/{p.name[:14]}:foreign', lambda: None, {'foreign_paths':[str(p)],'foreign_inodes':[str(p)]})]
only = sys.argv[1:]
CMDS={k:v for k,v in CMDS.items() if k in ('install',)}
CMDS['init']=([],('init','--json'))
CMDS['beh-validate']=([],('behavior','validate','examples/behavior/executive-secretary.yaml','--root',str(REPO),'--json'))
CMDS['config-validate']=([],('config','validate','--json'))
for name, make, scen in cases:
    if only and not any(o in name for o in only): continue
    print('##', name, flush=True)
    for cname,(script,argv) in CMDS.items():
        restore(); make()
        if scen and not all(os.path.lexists(x) for x in scen['foreign_paths']): print('   skip (path missing)'); break
        b1,b2=snap(ROOT),snap(VICT)
        t=time.time()
        try:
            r=model(P,script,*argv,stdin=(b'Find my next appointment\n' if cname=='chat-work' else None),**scen)
        except subprocess.TimeoutExpired:
            print(f'   {cname:14} HANG (timeout)'); subprocess.run(['pkill','-f',str(A/"runner.py")]); continue
        a1,a2=snap(ROOT),snap(VICT)
        ch=sorted(set(k for k in set(a1)|set(b1) if a1.get(k)!=b1.get(k))|set(k for k in set(a2)|set(b2) if a2.get(k)!=b2.get(k)))
        ch=[c.replace(str(A/'profiles')+'/','') for c in ch]
        try:
            v=json.loads(r[1].splitlines()[0]); s=(v['status'],(v.get('error') or {}).get('code'),(v.get('data') or {}).get('reason'),(v.get('data') or {}).get('component'))
        except Exception: s=('??',r[1][:100],r[2][-150:])
        spy=[x[0] for x in r[3] if x[0] in('handler','probe_call','request')]
        print(f'   {cname:14} exit={r[0]} {s} spy={spy} changed={[c[-60:] for c in ch][:6]}{"..." if len(ch)>6 else ""}', flush=True)
