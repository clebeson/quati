from h import *
import shutil, jsonschema
schema=json.loads((REPO/'contracts/runtime-boundaries.schema.json').read_text())
defs=schema.get('$defs') or schema.get('definitions'); print('schema defs:',sorted(defs))
def validate_response(v):
    try:
        jsonschema.validate(v,{**schema,'$ref':'#/$defs/Response'} if '$defs' in schema else {**schema,'$ref':'#/definitions/Response'}); return 'Response schema OK'
    except Exception as ex: return 'Response schema FAIL: '+str(ex).splitlines()[0][:200]
M01=['profile','os','os_qualification','python_version','sqlite_version','sqlite_fts5','sqlite_journal_mode','sqlite_journal_reason','sqlite_ok','config_dir','config_valid','provider','live_calls_allowed','listening_sockets','worker','policy','behavior','warnings']
def doc(label,r):
    c,o,e=r; v=json.loads(o); d=v['data']
    print(f"## {label}: exit {c} {v['status']} | {validate_response(v)} | stdout lines={len(o.splitlines())} stderr={e!r}")
    print('   missing M01 fields:',[k for k in M01 if k not in d],'| extra fields:',[k for k in d if k not in M01])
    print('   ',{k:d[k] for k in M01 if k in d and k not in('provider','behavior')})
    p=d['provider']; print('    provider:',{k:p.get(k) for k in ('status','measured_support','configured','reasons','features','feature_report','transport','model')})
    b=d['behavior']; print('    behavior:',{k:(v2[:12] if isinstance(v2,str) and len(v2)==64 else v2) for k,v2 in b.items()})
    return v
P='dc'; shutil.rmtree(A/P, ignore_errors=True); shutil.rmtree(A/(P+'-harness'), ignore_errors=True)
doc('before init',q(P,'doctor','--json')); print('   files created by doctor before init:',files(P))
doc('before init, QUATI_ALLOW_LIVE-less provider vars + key',q(P,'doctor','--json',extra={'QUATI_PROVIDER':'openai_compatible','QUATI_BASE_URL':'https://api.openai.com/v1','QUATI_MODEL':'m','QUATI_API_KEY_ENV':'K','K':'sk-CANARYKEY12345678901234567890'}))
q(P,'init','--json'); doc('after init',q(P,'doctor','--json'))
r=model3(P,[],'doctor','--probe','--json'); v=json.loads(r[1]); print('## scripted doctor --probe: exit',r[0],v['status'],validate_response(v),'provider.status',v['data']['provider']['status'],v['data']['provider'].get('measured_support'),'keys',sorted(v['data'])[:30])
doc('after scripted probe (same scripted config)',model3(P,[],'doctor','--json'))
doc('after scripted probe, DIFFERENT config (env default)',q(P,'doctor','--json'))
doc('after probe, QUATI_CAPABILITY_CONTEXT=1 (unauthenticated)',model3(P,[],'doctor','--json',extra={'QUATI_CAPABILITY_CONTEXT':'1'}))
# broken identity
os.chmod(A/P/'config/identity.json',0o644); v=doc('identity.json 0644',q(P,'doctor','--json')); print('   config validate:',q(P,'config','validate','--json')[1][:600]); os.chmod(A/P/'config/identity.json',0o600)
os.chmod(A/P/'config',0o755); v=doc('config dir 0755',q(P,'doctor','--json')); os.chmod(A/P/'config',0o700)
os.chmod(A/P/'config/policy.json',0o644) if (A/P/'config/policy.json').exists() else print('no policy.json', os.listdir(A/P/'config')); v=doc('policy.json 0644',q(P,'doctor','--json')); print('   config validate:',one(q(P,'config','validate','--json')))
