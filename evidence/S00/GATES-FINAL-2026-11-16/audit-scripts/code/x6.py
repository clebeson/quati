import sys,os,json,base64,stat; sys.path.insert(0,'.'); sys.path.insert(0,'<local-path>')
from h import *
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from quati.application.identity import canonical_bytes
W=[['classify'],['search','next appointment calendar'],['describe','fixtures.calendar-read'],['invoke','fixtures.calendar-read',{'limit':1}],['final','MODELTEXT ok']]
def acount():
    p=root("x6")/"data/capabilities/audit.jsonl"
    return len(p.read_text().splitlines()) if p.is_file() and p.stat().st_nlink==1 else -1
def case(name, mut):
    ready('x6'); r=root('x6'); mut(r)
    a0=acount()
    for argv,stdin in ((('ask','Find my next appointment','--json'),None),(('chat','--jsonl'),b'Find my next appointment\n')):
        o=model('x6',W,*argv,stdin=stdin)
        req=[x for x in o[3] if x[0]=='request']; left=[x for x in o[3] if x[0]=='script_left']
        try: v=json.loads(o[1].splitlines()[0]); s=(v['status'],(v.get('error') or {}).get('code'),(v.get('data') or {}).get('reason'),(v.get('data') or {}).get('provider_used'))
        except Exception as e: s=('??',o[1][:120],o[2][-120:])
        print(f'{name:22} {argv[0]:5} exit={o[0]} {s} requests={len(req)} script_left={left} handlers={[x for x in o[3] if x[0]=="handler"]} audit {a0}->{acount()}',flush=True)
def audit_fifo(r):
    p=r/'data/capabilities/audit.jsonl'; p.unlink(); os.mkfifo(p,0o600)
def audit_0644(r): os.chmod(r/'data/capabilities/audit.jsonl',0o644)
def reg_0644(r): os.chmod(r/'data/capabilities/registry.json',0o644)
def reg_link(r):
    p=r/'data/capabilities/registry.json'; os.link(p,r/'regalias')
def guest(r):
    p=r/'config/identity.json'; rec=json.loads(p.read_text()); rec.pop('signature'); rec['tenant_role']='GUEST'
    k=Ed25519PrivateKey.from_private_bytes((r/'config/device.key').read_bytes())
    s=dict(rec,signature=base64.b64encode(k.sign(canonical_bytes(rec))).decode()); p.write_bytes(canonical_bytes(s)); os.chmod(p,0o600)
for n,m in (('audit-fifo',audit_fifo),('audit-0644',audit_0644),('registry-0644',reg_0644),('registry-hardlink',reg_link),('guest-no-grant',guest)):
    case(n,m)
