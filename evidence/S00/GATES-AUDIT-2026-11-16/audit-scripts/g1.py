from h import *
sets = {
 'cred-missing': {'QUATI_PROVIDER':'anthropic','QUATI_MODEL':'claude-haiku-4-5','QUATI_BASE_URL':'https://api.anthropic.com','QUATI_API_KEY_ENV':'MY_SECRET_VAR'},
 'cred-present-no-live': {'QUATI_PROVIDER':'anthropic','QUATI_MODEL':'claude-haiku-4-5','QUATI_BASE_URL':'https://api.anthropic.com','QUATI_API_KEY_ENV':'MY_SECRET_VAR','MY_SECRET_VAR':'sk-CANARY-9f8e7d6c5b4a'},
 'bogus': {'QUATI_PROVIDER':'bogus-provider-xyz'},
 'bad-url-with-secret': {'QUATI_PROVIDER':'anthropic','QUATI_BASE_URL':'http://user:pwCANARY@evil.test/?k=sk-CANARY2','QUATI_API_KEY_ENV':'MY_SECRET_VAR','MY_SECRET_VAR':'sk-CANARY-9f8e7d6c5b4a'},
 'openai': {'QUATI_PROVIDER':'openai_compatible'},
 'claude_cli': {'QUATI_PROVIDER':'claude_cli'},
 'keyenv-is-value': {'QUATI_PROVIDER':'anthropic','QUATI_API_KEY_ENV':'sk-CANARY-direct-value'},
}
cmds = [['doctor','--json'],['doctor','--probe','--json'],['models','probe','--json'],['ask','hello','--json'],['ask','Hi, how are you?','--json'],['capabilities','list','--json'],['init','--json'],['ask','what is my next appointment','--json']]
for name,e in sets.items():
    print('=====',name)
    for c in cmds:
        code,out,err = q('g1',*c,extra=e)
        d=json.loads(out); p=(d.get('data') or {}).get('provider') or {}
        print(' ',' '.join(c),'-> exit',code,d['status'],(d.get('error') or {}).get('code'),'| kind',(d.get('data') or {}).get('result_kind'),'| prov',{k:p.get(k) for k in ('status','missing','reasons','transport','model','endpoint_host')} if p else '', '| CANARY' if 'CANARY' in out+err else '', '| STDERR:'+err[:200] if err else '')
