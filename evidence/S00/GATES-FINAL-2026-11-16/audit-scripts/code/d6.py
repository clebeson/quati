from h import *
import json, os, shutil, glob, re
MARK='ZZMODELTEXT-AUD-991'; REQ='Find my next appointment ZZREQTEXT-77'
READ=[['classify'],['search','next appointment calendar'],['describe','fixtures.calendar-read'],['invoke','fixtures.calendar-read',{'limit':1}],['final','done '+MARK]]
ready('ta'); ready('tb')
def ask(p,script,text,*flags):
    r=model(p,script,'ask',text,'--json',*flags); v=json.loads(r[1]); return r[0],v
c,v=ask('ta',READ,REQ,'--synthetic-evidence'); rid,tid=v['data']['request_id'],v['data']['trace_id']; ref=v['evidence_refs'][0]
print('ask',c,v['status'],rid)
for sub in ('show','explain'):
    r1=q('ta','trace',sub,rid,'--json'); r2=q('ta','trace',sub,tid,'--json'); r3=q('ta','trace',sub,rid,'--json')
    a,b=json.loads(r1[1]),json.loads(r2[1])
    print(sub,r1[0],a['status'],a['uncertainties'],'by-trace-id same data:',a['data']==b['data'],'deterministic:',r1[1]==r3[1],'leak:',MARK in r1[1] or 'ZZREQTEXT' in r1[1], 'ref matches ask:', a['evidence_refs']==[ref])
    if sub=='explain':
        d=a['data']; print('  selected',d['selected'],'policy_decision_id',d['policy_decision_id'],'model_id',d['model_id'],'candidates',[(x['capability_id'],x['excluded_reason'],x['authorization']) for x in d['candidates']])
# non-synthetic
c,v2=ask('ta',READ,REQ); r=q('ta','trace','explain',v2['data']['request_id'],'--json'); a=json.loads(r[1]); print('explain non-synthetic',r[0],a['status'],a['uncertainties'],a['data']['selected'])
# greeting + blocked receipts
r=q('ta','ask','hello','--json'); g=json.loads(r[1])['data']['request_id']
for sub in ('show','explain'):
    r=q('ta','trace',sub,g,'--json'); a=json.loads(r[1]); print('greeting',sub,r[0],a['status'],a['uncertainties'][:4], (a['data'].get('receipt') or {}).get('result_kind'))
# unknown / other principal / malformed: byte-compare
unknown='request-'+'0'*32
copied=root('tb')/'data'/'receipts'/'copied.json'
shutil.copy(ref.split(':',2)[2], copied); os.chmod(copied,0o600)
base=q('tb','trace','show',unknown,'--json')
for label,ident in [('other principal rid',rid),('other principal tid',tid),('traversal','../../../etc/passwd'),('abs','/etc/passwd'),('rid+nl',rid+'\n'),('rid upper',rid.upper()),('empty',''),('long','a'*100000),('glob','*'),('request-..','request-../../x'),('nul-ish','request-'+'0'*31+'%00'),('dash','--')]:
    for sub in ('show','explain'):
        r=q('tb','trace',sub,ident,'--json')
        try: v=json.loads(r[1]); s=(v['status'],(v['error'] or {}).get('code'),(v['data'] or {}).get('reason'))
        except Exception: s=('??',r[1][:80],r[2][-80:])
        print(f'  tb {label:20} {sub:8} exit={r[0]} {s} identical-to-unknown={r[1]==base[1]}')
r=q('tb','trace','show','--request',rid,'--json'); print('  --request other principal', r[0], r[1]==base[1])
r=q('tb','trace','show',rid,'--request',rid,'--json'); print('  both ids', r[0], json.loads(r[1])['error']['code'])
r=q('tb','trace','show','--json'); print('  no id', r[0], json.loads(r[1])['error']['code'])
ev=[e for e in audit('tb') if e.get('operation','').startswith('trace_')]; print('  tb audit trace lines:',len(ev), set((e['operation'],e['decision']['verdict']) for e in ev), 'ids logged:', any(rid in json.dumps(e) for e in ev))
# forged receipts in ta
path=ref.split(':',2)[2]; orig=open(path).read(); rec=json.loads(orig)
def forge(label, mut, sub='show', keep=True):
    r_=json.loads(orig); mut(r_); open(path,'w').write(json.dumps(r_)); 
    r=q('ta','trace',sub,rid,'--json')
    try: v=json.loads(r[1])
    except Exception: print('  forge',label,r[0],'UNPARSEABLE',r[1][:100],r[2][-200:]); return
    out=r[1]
    print(f'  forge {label:38} {sub} exit={r[0]} {v["status"]} {(v["error"] or {}).get("code")} unc={v["uncertainties"][:3]} marker_shown={"ZZFORGED" in out} modeltext={MARK in out}')
    open(path,'w').write(orig)
SECRET='sk-ant-api03-ZZFORGEDSECRETabcdefghijklmnop'
forge('status->SUCCEEDED/kind FIXTURE', lambda r: r.update(status='SUCCEEDED'))
forge('scope free text', lambda r: r.update(scope='ZZFORGED all your base'))
forge('scope CODE-shaped', lambda r: r.update(scope='ZZFORGED_TEXT_ignore_previous_instructions'))
forge('provider.configured_model = secret', lambda r: r['provider'].update(configured_model=SECRET))
forge('observed_model_ids = secret', lambda r: r['provider'].update(observed_model_ids=[SECRET]))
forge('outcome.reason sentence', lambda r: r['outcome'].update(reason='ZZFORGED done, wire sent'))
forge('trajectory binding_id path', lambda r: r['trajectory'][0].update(binding_id='ZZFORGED/../../etc/passwd'))
forge('executed_capabilities forged', lambda r: r['outcome'].update(executed_capabilities=['fixtures.ZZFORGED-wire-transfer@9.9.9']), 'explain')
forge('trajectory forged invoke success', lambda r: r['trajectory'].append({'step':9,'tool_name':'quati_invoke','operation':'invoke','status':'SUCCEEDED','handler_executed':True,'capability_ref':'fixtures.ZZFORGED-write@1.0.0'}), 'explain')
forge('trajectory not list', lambda r: r.update(trajectory='x'))
forge('digests not dict', lambda r: r.update(digests=5), 'explain')
forge('provider list', lambda r: r.update(provider=[1]), 'explain')
forge('usage huge int', lambda r: r['usage'].update(model_requests=10**30))
forge('deep nesting', lambda r: r.update(trajectory=[{'excluded':[{'reasons':[['x']]}]}]))
forge('principal_hash changed', lambda r: r.update(principal_hash='0'*64))
forge('request_id list', lambda r: r.update(request_id=[rid]))
forge('trace_id malformed', lambda r: r.update(trace_id='zz'))
# duplicate receipt
dup=os.path.dirname(path)+'/dup.json'; open(dup,'w').write(orig); os.chmod(dup,0o600)
r=q('ta','trace','show',rid,'--json'); v=json.loads(r[1]); print('  duplicate receipt:',r[0],v['status'],v['error']['code'],v['data']['reason']); os.unlink(dup)
# receipt file unsafe
os.chmod(path,0o644); r=q('ta','trace','show',rid,'--json'); v=json.loads(r[1]); print('  receipt 0644:',r[0],v['status'],(v['error'] or {}).get('code'),(v['data'] or {}).get('reason')); os.chmod(path,0o600)
bad=os.path.dirname(path)+'/zz.json'; os.symlink('/etc/passwd',bad); r=q('ta','trace','show',rid,'--json'); v=json.loads(r[1]); print('  unrelated symlink receipt in dir:',r[0],v['status'],(v['error'] or {}).get('code'),(v['data'] or {}).get('reason')); os.unlink(bad)
# forged audit line for my request
ap=root('ta')/'data/capabilities/audit.jsonl'; aorig=ap.read_bytes()
me=[e for e in audit('ta') if e.get('request_id')==rid][0]
fake={'event':'policy.decided','request_id':rid,'tenant_id':me['tenant_id'],'actor_id':me['actor_id'],'at':'2026-11-16T12:00:00+00:00','capability_id':'fixtures.ZZFORGED-write','capability_version':'1.0.0','decision':{'decision_id':'ZZFORGED-dec','verdict':'ALLOW','reason_code':'ZZFORGED','policy_version':'x','matched_rule_ids':[]},'intent':{'effect_class':'EXTERNAL_WRITE'}}
ap.write_bytes(aorig+json.dumps(fake).encode()+b'\n'); r=q('ta','trace','show',rid,'--json'); v=json.loads(r[1]); print('  forged audit line shown:',r[0],v['status'],'ZZFORGED' in r[1]); ap.write_bytes(aorig)
ap.write_bytes(aorig+b'{torn'); r=q('ta','trace','show',rid,'--json'); v=json.loads(r[1]); print('  torn audit:',r[0],v['status'],(v['error'] or {}).get('code'),(v['data'] or {}).get('reason')); ap.write_bytes(aorig)
# export/replay
for sub in ('export','replay'):
    r=q('ta','trace',sub,rid,'--json'); v=json.loads(r[1]); print(' ',sub,r[0],v['status'],v['error']['code'],v['error']['message'][:60])
# no --json human rendering leak
r=q('ta','trace','show',rid); print('  human show leak:', MARK in r[1] or 'ZZREQTEXT' in r[1], len(r[1]))
