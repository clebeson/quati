from h import *
import json, os, shutil, stat, subprocess, sys, hashlib, time
P='m'; ROOT=root(P); TPL=A/'profiles'/'m-template'; VICT=A/'profiles'/'m-victim'
READ=[['classify'],['search','next appointment calendar'],['describe','fixtures.calendar-read'],['invoke','fixtures.calendar-read',{'limit':1}],['final','done']]
if TPL.exists(): shutil.rmtree(TPL)
ready(P)
r=model(P,READ,'ask','Find my next appointment','--json'); assert r[0]==0, r
RID=json.loads(r[1])['data']['request_id']
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
D=ROOT/'data'
CMDS={
 'list':([], ('capabilities','list','--json')),
 'install':([], ('capabilities','install-fixture','forecast-read','--enable-fixture','--json')),
 'disable':([], ('capabilities','disable','fixtures.calendar-read@1.0.0','--json')),
 'work-ask':(READ, ('ask','Find my next appointment','--json')),
 'chat':(READ, ('chat','--jsonl')),
 'trace-show':([], ('trace','show',RID,'--json')),
}
def lines():
    p=D/'capabilities/audit.jsonl'
    try:
        if p.is_symlink() or not p.is_file(): return 'n/a'
        return len(p.read_bytes().splitlines())
    except OSError: return 'n/a'
def revision():
    p=D/'capabilities/registry.json'
    try:
        if p.is_symlink() or not p.is_file(): return 'n/a'
        return json.loads(p.read_text()).get('revision')
    except Exception: return 'n/a'
def sym(p):
    t=VICT/p.name
    if p.exists(): shutil.move(str(p),str(t))
    else: t.write_bytes(b'')
    os.symlink(t,p)
def fifo(p):
    if p.is_dir(): shutil.rmtree(p)
    elif p.exists(): os.unlink(p)
    os.mkfifo(p,0o600)
def hard(p): os.link(p,VICT/(p.name+'.hard'))
def mode(p,m=0o644): os.chmod(p,m)
def isdir(p):
    os.unlink(p); os.mkdir(p)
def isfile(p):
    shutil.rmtree(p); p.write_text('x')
PK=D/'capabilities/packages'
MAN=PK/'fixtures.calendar-read/1.0.0/capability.scs.json'
cases=[]
cases+=[('packages:symlink',PK,sym,{}),('packages:foreign',PK,lambda p:None,{'foreign_paths':[str(PK)],'foreign_inodes':[str(PK)]}),
        ('packages:regular-file',PK,isfile,{}),('packages:mode0500',PK,lambda p:mode(p,0o500),{})]
for nm,p in (('registry.json',D/'capabilities/registry.json'),('capabilities.lock',D/'capabilities/capabilities.lock'),('registry.flock',D/'capabilities/registry.flock'),('audit.jsonl',D/'capabilities/audit.jsonl'),('manifest',MAN)):
    cases+=[(f'{nm}:fifo',p,fifo,{}),(f'{nm}:symlink',p,sym,{}),(f'{nm}:hardlink',p,hard,{}),(f'{nm}:mode0644',p,mode,{}),(f'{nm}:directory',p,isdir,{}),
            (f'{nm}:foreign',p,lambda p:None,{'foreign_paths':[str(p)],'foreign_inodes':[str(p)]})]
only=sys.argv[1:]
for name,p,make,scen in cases:
    if only and not any(o in name for o in only): continue
    print('##',name,flush=True)
    for cname,(script,argv) in CMDS.items():
        restore(); make(p)
        b1,b2=snap(ROOT),snap(VICT); l0=lines(); r0=revision(); t=time.time()
        try:
            r=model(P,script,*argv,stdin=(b'Find my next appointment\n' if cname=='chat' else None),**scen)
        except subprocess.TimeoutExpired:
            print(f'   {cname:10} HANG(20s) lines {l0}->? '); subprocess.run(['pkill','-f','fix7_public_runner']); continue
        a1,a2=snap(ROOT),snap(VICT)
        ch=sorted(set(k for k in set(a1)|set(b1) if a1.get(k)!=b1.get(k))|set(k for k in set(a2)|set(b2) if a2.get(k)!=b2.get(k)))
        ch=[c.replace(str(A/'profiles')+'/','').replace('m/data/','') for c in ch]
        try:
            v=json.loads(r[1].splitlines()[0]); s=(v['status'],(v.get('error') or {}).get('code'),(v.get('data') or {}).get('reason'),(v.get('data') or {}).get('component'))
        except Exception: s=('??',r[1][:80],r[2][-120:])
        spy=[x[0] for x in r[3] if x[0] in('handler','request')]
        print(f'   {cname:10} {time.time()-t:4.1f}s exit={r[0]} {s} spy={spy} lines {l0}->{lines()} rev {r0}->{revision()} changed={ch[:5]}',flush=True)
