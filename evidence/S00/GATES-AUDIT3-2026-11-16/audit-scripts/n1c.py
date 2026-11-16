from h import *
import json, os, shutil
def lif(p):
    r=q(p,'capabilities','list','--json'); 
    try: return {c['capability_id']:c['lifecycle'] for c in json.loads(r[1])['data']['capabilities']}
    except Exception: return (r[0], r[1][:200])
INST=('capabilities','install-fixture','forecast-quick','--enable-fixture','--json')
# (a) packages dir symlinked to a directory outside the data dir
ready('c1'); V=root('c1')/'victim'; D=root('c1')/'data'
shutil.move(str(D/'capabilities'/'packages'), str(V)); os.symlink(V, D/'capabilities'/'packages')
before=set(str(p.relative_to(V)) for p in V.rglob('*'))
r=q('c1',*INST); v=json.loads(r[1]); after=set(str(p.relative_to(V)) for p in V.rglob('*'))
print('(a) packages -> symlink: install exit',r[0],v['status'],(v['error'] or {}).get('code'),(v['data'] or {}).get('reason'))
print('    files created THROUGH the symlink in the outside directory:', sorted(after-before))
print('    lifecycles:', lif('c1'))
r=model('c1',[['classify'],['search','forecast weekly order volume region'],['describe','fixtures.forecast-quick'],['invoke','fixtures.forecast-quick',{'region':'north','weeks':1}],['final','x']],'ask','Forecast orders for north next week','--json'); v=json.loads(r[1])
print('    ask using package read through symlink: exit',r[0],v['status'],v['data']['result_kind'],[(t['operation'],t['status'],t['reason']) for t in v['data']['tool_calls']],'handlers',[x for x in r[3] if x[0]=='handler'])
# (a2) per-id package dir symlink / staging symlink
ready('c2'); D=root('c2')/'data'; V=root('c2')/'victim'; V.mkdir()
os.symlink(V, D/'capabilities'/'staging') if not (D/'capabilities'/'staging').exists() else (shutil.rmtree(D/'capabilities'/'staging'), os.symlink(V, D/'capabilities'/'staging'))
r=q('c2',*INST); v=json.loads(r[1]); print('(a2) staging -> symlink: install exit',r[0],v['status'],(v['error'] or {}).get('code'),(v['data'] or {}).get('reason'),'victim now has',sorted(str(p.relative_to(V)) for p in V.rglob('*'))[:4], lif('c2'))
# (b) publish fails after commit
for label,make in (('packages is a regular file', lambda p: (shutil.rmtree(p), p.write_text('x'))), ('packages mode 0500', lambda p: os.chmod(p,0o500))):
    ready('c3'); D=root('c3')/'data'; make(D/'capabilities'/'packages'); a0=len(audit('c3')); l0=lif('c3') if 'file' not in label else None
    reg0=json.loads((D/'capabilities'/'registry.json').read_text())['revision']
    r=q('c3',*INST); v=json.loads(r[1]); reg1=json.loads((D/'capabilities'/'registry.json').read_text())
    print(f'(b) {label}: install exit',r[0],v['status'],v['error']['code'],'|',v['error']['message'],'|',v['next_action'])
    print('    registry revision',reg0,'->',reg1['revision'],'; new audit events:',[e['event'] for e in audit('c3')[a0:]])
    print('    registry now records:', {k:(x.get('lifecycle')) for k,x in (reg1.get('records') or reg1.get('capabilities') or {}).items()} if isinstance(reg1.get('records') or reg1.get('capabilities'),dict) else list(reg1)[:8])
    os.chmod(D/'capabilities'/'packages',0o700) if (D/'capabilities'/'packages').is_dir() else None
    print('    list afterwards:', lif('c3'))
    r=q('c3',*INST); v=json.loads(r[1]); print('    retry install: exit',r[0],v['status'],(v['error'] or {}).get('code'),(v['data'] or {}).get('reason'))
# (c) registry.json replaced by symlink to attacker-chosen registry content
ready('c4'); D=root('c4')/'data'; reg=D/'capabilities'/'registry.json'; outside=root('c4')/'outside-registry.json'
shutil.copy(reg, outside); os.chmod(outside,0o666); reg.unlink(); os.symlink(outside, reg)
r=q('c4','capabilities','list','--json'); print('(c) registry.json -> symlink to a 0666 file outside the data dir: list exit',r[0],json.loads(r[1])['status'], lif('c4'))
