import sys,os,json,base64,shutil; sys.path.insert(0,'.'); sys.path.insert(0,'<local-path>')
from h import *
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from quati.application.identity import canonical_bytes
P='x11'
def resign(mut):
    c=root(P)/'config'; k=Ed25519PrivateKey.from_private_bytes((c/'device.key').read_bytes())
    rec=json.loads((c/'identity.json').read_text()); rec.pop('signature'); mut(rec)
    s=dict(rec,signature=base64.b64encode(k.sign(canonical_bytes(rec))).decode()); p=c/'identity.json'; p.write_bytes(canonical_bytes(s)); os.chmod(p,0o600)
def run(name):
    out=[]
    for argv in (('doctor','--json'),('config','validate','--json'),('capabilities','list','--json'),('ask','hi','--json'),('trace','show','x','--json')):
        r=q(P,*argv); 
        try: v=json.loads(r[1].splitlines()[0]); out.append((argv[0],r[0],v['status'],(v.get('error') or {}).get('code'), (v.get('data') or {}).get('identity') if argv[0]=='doctor' else None))
        except Exception: out.append((argv[0],r[0],'??',r[2][-80:]))
    print(name); [print('   ',o) for o in out]
def setup():
    fresh(P); assert q(P,'init','--json')[0]==0
setup(); resign(lambda r:r.__setitem__('principal_id','01M7KDG6T083PFGR8AHBEMPZNV')); run('valid ULID but different principal (control)')
