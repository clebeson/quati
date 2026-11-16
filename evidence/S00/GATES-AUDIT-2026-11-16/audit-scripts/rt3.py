from h import *
import shutil
SESSION='{"OPENAI_API_KEY": null, "tokens": {"id_token": "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ4In0.c2lnCANARY", "access_token": "eyJhbGciOiJSUzI1NiJ9.eyJhdWQiOiJjaGF0Z3B0In0.c2lnCANARY", "refresh_token": "rt_CANARY", "account_id": "acc"}, "last_refresh": "2026-11-01T00:00:00Z"}'
base={'QUATI_PROVIDER':'openai_compatible','QUATI_BASE_URL':'https://api.openai.com/v1','QUATI_MODEL':'gpt-tools-pro','QUATI_API_KEY_ENV':'CODEX_SESSION'}
for label,val in (('session-file contents',SESSION),('bare session JWT','eyJhbGciOiJSUzI1NiJ9.eyJhdWQiOiJjaGF0Z3B0In0.c2lnCANARY'),('path ~/.codex/auth.json','~/.codex/auth.json'),('file: ref','file:~/.codex/auth.json')):
    c,o,e=q('g1','doctor','--json',extra={**base,'CODEX_SESSION':val}); p=json.loads(o)['data']['provider']
    print(label,'-> exit',c,'reasons',p['reasons'],'features',set(p['features'].values()),'| CANARY leaked' if 'CANARY' in o+e else '| no leak')
# in-process: with allow_live True (no call is made by diagnostics) would the session blob count as configured?
import sys; sys.path.insert(0,str(REPO/'src'))
from quati.application.ports import ProviderConfig
from quati.application.providers import create_provider
for label,val in (('session-file contents',SESSION),('bare session JWT','eyJhbGciOiJSUzI1NiJ9.e30.c2ln')):
    prov=create_provider(ProviderConfig(base_url='https://api.openai.com/v1',model='gpt-tools-pro',api_key_env='CODEX_SESSION',allow_live=True,transport='openai_compatible'),environ={'CODEX_SESSION':val}) if 'environ' in create_provider.__code__.co_varnames or True else None
    try: d=prov.diagnostics(); print('in-process allow_live=True,',label,': configured =',d['configured'],d['reasons'])
    except Exception as ex: print('diag error',type(ex).__name__,ex)
# gap 2: unauthenticated probe writes evidence + feature report
P='noid'; shutil.rmtree(A/P,ignore_errors=True); shutil.rmtree(A/(P+'-harness'),ignore_errors=True)
c,o,e=model(P,[],'models','probe','--json'); d=json.loads(o); print('probe with NO identity: exit',c,d['status'],'files written:',sorted(str(p.relative_to(A/P)) for p in (A/P).rglob('*') if p.is_file())[:6])
c,o,e=model(P,[],'doctor','--probe','--json'); d=json.loads(o); print('doctor --probe with NO identity: exit',c,d['status'],'identity',d['data']['identity']['status'])
c,o,e=model(P,[],'models','probe','--json',extra={'QUATI_CAPABILITY_CONTEXT':'1'}); print('probe inside QUATI_CAPABILITY_CONTEXT: exit',c,json.loads(o)['status'])
# doctor after probe: does plain doctor report measured support for the same config?
P='g3'
c,o,e=model(P,[],'doctor','--json'); p=json.loads(o)['data']['provider']; print('doctor (same fake config, after successful probe):',{k:p.get(k) for k in ('status','configured','features')})
# forged feature report pointer for a never-probed config
P='forge'; shutil.rmtree(A/P,ignore_errors=True); shutil.rmtree(A/(P+'-harness'),ignore_errors=True)
q(P,'init','--json'); q(P,'capabilities','install-fixture','calendar-read','--enable-fixture','--json')
READ=[['classify'],['search','next appointment calendar'],['describe','fixtures.calendar-read'],['invoke','fixtures.calendar-read',{'limit':1}],['final','done']]
c,o,e=model(P,READ,'ask','--json','Find my next appointment'); print('ask with NO probe:',c,brief(o)[0]['status'],brief(o)[0]['code'],brief(o)[0]['unc'])
# copy a genuine report+pointer from another profile (g3) into this one = replayed/forged measurement
import hashlib,glob
src=A/'g3'/'data'/'feature_reports'; ptrs=list(src.glob('*.json')); ptr=json.loads(ptrs[0].read_text()); rep=json.loads(open(ptr['receipt_path']).read())
rep['features']['tools']='SUPPORTED'; rep['measured_at']=rep['measured_at']
dst=A/P/'data'/'receipts'; dst.mkdir(parents=True,exist_ok=True); blob=(json.dumps(rep,indent=2,sort_keys=True)+'\n').encode(); rp=dst/'forged.json'; rp.write_bytes(blob)
fr=A/P/'data'/'feature_reports'; fr.mkdir(parents=True,exist_ok=True); (fr/ptrs[0].name).write_text(json.dumps({**ptr,'receipt_path':str(rp),'receipt_sha256':hashlib.sha256(blob).hexdigest()}))
c,o,e=model(P,READ,'ask','--json','Find my next appointment'); b=brief(o)[0]; print('ask with HAND-WRITTEN feature report (no probe ever run in this profile):',c,b['status'],b['code'],b['kind'],b['tool_calls'])
