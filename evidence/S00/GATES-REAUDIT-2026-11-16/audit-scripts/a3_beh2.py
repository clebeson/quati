from h import *
import shutil, hashlib
exec(open(A/'a3_beh.py').read().split('lib={}')[0].split('from h import *')[1].replace("shutil.rmtree(A/P, ignore_errors=True); assert q(P,'init','--json')[0]==0",""))
def st(profile):
    r=A/profile/'data'
    return sorted(str(p.relative_to(r)) for p in r.rglob('*')) if r.exists() else []
def show(label,r):
    c,o,e=r
    try:
        v=json.loads(o); d=v.get('data') or {}
        print(f"{label}: exit {c} {v['status']} code={(v.get('error') or {}).get('code')} diags={[x['code']+' '+x['reason']+' at '+x['path'] for x in (d.get('diagnostics') or [])][:3]} package={d.get('package')!r} hashes={(d.get('behavior_hash') or '')[:10]},{(d.get('statechart_hash') or '')[:10]},{(d.get('prompt_hash') or '')[:10]} keys={sorted(d)[:12]} abs_path_in_out={str(A) in o or '/home/' in o} stderr={e[-160:]!r}")
        return v
    except Exception as ex: print(f"{label}: exit {c} NONJSON({type(ex).__name__}) out={o[:160]!r} err={e[-300:]!r}")
s0=st(P)
print('## shipped examples')
for f in ('executive-secretary.yaml','incident-analyst.yaml'):
    show(f'validate {f}',bv('validate','examples/behavior/'+f,REPO)); show(f'render {f}',bv('render','examples/behavior/'+f,REPO))
v=json.loads(bv('validate','examples/behavior/executive-secretary.yaml',REPO)[1]); ref=json.loads((REPO/'examples/behavior/compiled_receipt.reference.json').read_text())
print('validate hashes == reference file:',all(v['data'][k]==ref[k] for k in ('behavior_hash','statechart_hash','prompt_hash')))
r=json.loads(bv('render','examples/behavior/executive-secretary.yaml',REPO)[1])['data']; print('render keys:',sorted(r), '| text == prompt_preview.reference:', r.get('text')==(REPO/'examples/behavior/prompt_preview.reference.txt').read_text() if 'text' in r else None)
print('## determinism through the CLI')
outs=set(); outs_r=set()
for x in ({'PYTHONHASHSEED':'0'},{'PYTHONHASHSEED':'1'},{'PYTHONHASHSEED':'4242','TZ':'Asia/Tokyo','LANG':'pt_BR.UTF-8'},{'PYTHONHASHSEED':'random','LC_ALL':'C'},{'PYTHONHASHSEED':'random','TZ':'America/Sao_Paulo','LC_ALL':'tr_TR.UTF-8'},{'PYTHONHASHSEED':'7','PYTHONUTF8':'0','LC_ALL':'POSIX'}):
    outs.add(bv('validate','examples/behavior/executive-secretary.yaml',REPO,extra=x)[1]); outs_r.add(bv('render','examples/behavior/executive-secretary.yaml',REPO,extra=x)[1])
print('validate stdout byte-identical across 6 envs:',len(outs)==1,'| render:',len(outs_r)==1)
print('abs package inside root:'); show('  validate',bv('validate',str(REPO/'examples/behavior/executive-secretary.yaml'),REPO))
print('cwd default root:'); show('  validate',bv('validate','examples/behavior/executive-secretary.yaml',None,cwd=str(REPO)))
print('## hostile inputs')
H=A/'bh-roots'; shutil.rmtree(H,ignore_errors=True); H.mkdir()
base=A/'g4roots/baseline'
show('traversal ../baseline/p.yaml',bv('validate','../baseline/p.yaml',A/'g4roots/escape'))
show('traversal x/../../baseline/p.yaml',bv('validate','x/../../baseline/p.yaml',A/'g4roots/escape'))
show('absolute outside root',bv('validate',str(base/'p.yaml'),H))
show('absolute /etc/passwd',bv('validate','/etc/passwd',H))
show('relative ../../../../../../etc/passwd',bv('validate','../../../../../../../../../../etc/passwd',H))
show('nonexistent',bv('validate','nope.yaml',H))
os.symlink(base/'p.yaml',H/'link.yaml'); show('package is symlink out of root',bv('validate','link.yaml',H))
os.symlink('/etc/passwd',H/'pw.yaml'); show('package symlink -> /etc/passwd',bv('validate','pw.yaml',H))
os.symlink(base,A/'bh-rootlink') if not os.path.lexists(A/'bh-rootlink') else None; show('root itself is a symlink',bv('validate','p.yaml',A/'bh-rootlink'))
(H/'dir.yaml').mkdir(); show('package is a directory',bv('validate','dir.yaml',H))
(H/'bin.yaml').write_bytes(os.urandom(4096)); show('binary garbage',bv('validate','bin.yaml',H))
(H/'nul.yaml').write_bytes(b'id: a\x00b\n'); show('NUL in file',bv('validate','nul.yaml',H))
(H/'deep.yaml').write_text('['*20000+']'*20000); show('20000-deep flow nesting',bv('validate','deep.yaml',H))
(H/'deep2.yaml').write_text(''.join(' '*i+'a:\n' for i in range(3000))); show('3000-deep block nesting',bv('validate','deep2.yaml',H))
(H/'bomb.yaml').write_text('a: &a [x,x,x,x,x,x,x,x,x]\nb: &b [*a,*a,*a,*a,*a,*a,*a,*a,*a]\nc: &c [*b,*b,*b,*b,*b,*b,*b,*b,*b]\nd: &d [*c,*c,*c,*c,*c,*c,*c,*c,*c]\ne: &e [*d,*d,*d,*d,*d,*d,*d,*d,*d]\nf: &f [*e,*e,*e,*e,*e,*e,*e,*e,*e]\ng: &g [*f,*f,*f,*f,*f,*f,*f,*f,*f]\nh: [*g,*g,*g,*g,*g,*g,*g,*g,*g]\n'); 
import time; t=time.time(); show('yaml billion laughs',bv('validate','bomb.yaml',H)); print('   seconds',round(time.time()-t,1))
with open(H/'huge.yaml','w') as f:
    f.write('id: x\nnotes: "'); f.write('A'*(64*1024*1024)); f.write('"\n')
t=time.time(); show('64 MB package',bv('validate','huge.yaml',H)); print('   seconds',round(time.time()-t,1)); os.unlink(H/'huge.yaml')
# statechart huge/deep
d=H/'bigchart'; shutil.copytree(base,d); (d/'chart.yaml').write_text('['*20000+']'*20000); show('statechart 20000-deep',bv('validate','p.yaml',d))
show('package arg with newline',bv('validate','p.yaml\nx',base)); show('package arg empty',bv('validate','',base)); show('root nonexistent',bv('validate','p.yaml',A/'nope-root'))
show('root is a file',bv('validate','p.yaml',base/'p.yaml'))
os.mkfifo(H/'fifo.yaml')
try: show('package is FIFO',bv('validate','fifo.yaml',H))
except subprocess.TimeoutExpired: print('package is FIFO: HANG (timeout 120s)')
print('## identity')
shutil.rmtree(A/'bh-noid',ignore_errors=True)
show('no identity, existing package',bv('validate','p.yaml',base,profile='bh-noid')); show('no identity, missing package',bv('validate','nope.yaml',base,profile='bh-noid')); show('no identity, invalid package',bv('render','p.yaml',A/'g4roots/orphan-state',profile='bh-noid'))
show('QUATI_CAPABILITY_CONTEXT=1',bv('validate','p.yaml',base,extra={'QUATI_CAPABILITY_CONTEXT':'1'}))
print('data dir unchanged by all behavior commands:',st(P)==s0, '| noid profile created files:', [str(p) for p in (A/'bh-noid').rglob('*')] if (A/'bh-noid').exists() else [])
for name in ('propose','simulate','diff','promote','rollback'):
    show(f'behavior {name}',q(P,'behavior',name,'x','--json'))
