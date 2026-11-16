from h import *
import json, base64, os, sys, shutil
sys.path.insert(0,str(REPO/'src'))
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from quati.application.identity import canonical_bytes
P='id'
def setup():
    fresh(P); assert q(P,'init','--json')[0]==0
    q(P,'capabilities','install-fixture','calendar-read','--enable-fixture','--json')
def resign(mut):
    c=root(P)/'config'; key=Ed25519PrivateKey.from_private_bytes((c/'device.key').read_bytes())
    rec=json.loads((c/'identity.json').read_text()); rec.pop('signature'); mut(rec)
    signed=dict(rec, signature=base64.b64encode(key.sign(canonical_bytes(rec))).decode())
    os.chmod(c/'identity.json',0o600); (c/'identity.json').write_bytes(canonical_bytes(signed))
def show(label, cmds=(('doctor','--json'),('config','validate','--json'),('ask','hello','--json'),('capabilities','list','--json'),('capabilities','install-fixture','mail-search','--enable-fixture','--json'),('trace','show','0'*32,'--json'))):
    print('##',label)
    for c in cmds:
        r=q(P,*c)
        try:
            v=json.loads(r[1]); d=v.get('data') or {}
            extra=''
            if c[0]=='doctor': extra=f" identity={ {k:d['identity'].get(k) for k in ('status','reason','detail','initialized')} } warnings={d['warnings']} config_dir={d.get('config_dir')}"
            if c[0]=='config': extra=f" checks={[(x['name'],x['status'],x['reasons']) for x in d['checks']][:1]} next={v['next_action'][:50] if v['next_action'] else None}"
            print('  ',' '.join(c[:2]),r[0],v['status'],(v['error'] or {}).get('code'),d.get('reason'),extra, ('STDERR:'+r[2][-120:]) if r[2] else '')
            if str(root(P)) in r[1]+r[2] and v['status']!='SUCCEEDED' and (v['error'] or {}).get('code')=='UNAUTHENTICATED': print('   !!! path disclosed to unauthenticated caller')
        except Exception as e: print('  ',c[:2],r[0],'UNPARSEABLE',r[1][:200],r[2][-300:])
def case(label, fn):
    setup(); fn(); show(label)
c=lambda: root(P)/'config'
case('baseline', lambda: None)
case('identity.json 0644', lambda: os.chmod(c()/'identity.json',0o644))
case('config dir 0755', lambda: os.chmod(c(),0o755))
case('device.key 0640', lambda: os.chmod(c()/'device.key',0o640))
case('device.key missing', lambda: os.unlink(c()/'device.key'))
case('identity.json garbage', lambda: (c()/'identity.json').write_text('{not json'))
case('identity.json empty', lambda: (c()/'identity.json').write_text(''))
case('identity.json is dir', lambda: (os.unlink(c()/'identity.json'), os.mkdir(c()/'identity.json')))
case('identity.json fifo', lambda: (os.unlink(c()/'identity.json'), os.mkfifo(c()/'identity.json',0o600)))
case('identity.json symlink', lambda: (shutil.move(str(c()/'identity.json'), str(root(P)/'x.json')), os.symlink(root(P)/'x.json', c()/'identity.json')))
case('identity.json hardlink', lambda: os.link(c()/'identity.json', root(P)/'hl.json'))
case('config dir symlink', lambda: (shutil.move(str(c()), str(root(P)/'realcfg')), os.symlink(root(P)/'realcfg', c())))
case('unsigned edit', lambda: (c()/'identity.json').write_text((c()/'identity.json').read_text().replace('"owner_uid"','"owner_uid" ')))
for name,mut in [('missing organization_space_id', lambda r: r.pop('organization_space_id')), ('empty tenant_id', lambda r: r.update(tenant_id='')),
                 ('tenant_id int', lambda r: r.update(tenant_id=5)), ('tenant_id traversal', lambda r: r.update(tenant_id='../../../x')),
                 ('tenant_id whitespace', lambda r: r.update(tenant_id=' ')), ('tenant_id with newline+ansi', lambda r: r.update(tenant_id='T\n\x1b[31mX')),
                 ('principal_id 10k chars', lambda r: r.update(principal_id='A'*10000)),
                 ('owner_uid float', lambda r: r.update(owner_uid=float(os.getuid()))), ('owner_uid str', lambda r: r.update(owner_uid=str(os.getuid()))),
                 ('tenant_role MEMBER', lambda r: r.update(tenant_role='MEMBER')), ('tenant_role GUEST', lambda r: r.update(tenant_role='GUEST')),
                 ('tenant_role list', lambda r: r.update(tenant_role=['OWNER'])), ('tenant_role owner lowercase', lambda r: r.update(tenant_role='owner')),
                 ('schema_version other', lambda r: r.update(schema_version='evil/9')), ('extra field', lambda r: r.update(is_admin=True)),
                 ('same personal and org space', lambda r: r.update(organization_space_id=r['personal_space_id']))]:
    case('signed: '+name, lambda mut=mut: resign(mut))
os.environ.pop('X',None)
setup(); print('## QUATI_CAPABILITY_CONTEXT=1')
for cmd in (('doctor','--json'),('ask','hello','--json'),('trace','show','0'*32,'--json'),('init','--json')):
    r=q(P,*cmd,extra={'QUATI_CAPABILITY_CONTEXT':'1'}); v=json.loads(r[1]); print('  ',cmd[:2],r[0],v['status'],(v['error'] or {}).get('code'), str(root(P)) in r[1])
