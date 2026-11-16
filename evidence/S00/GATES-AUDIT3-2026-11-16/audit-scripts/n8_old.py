import sys,shutil,base64
sys.path.insert(0,'<local-path>')

import shutil, base64

C='CANARY7x9'
J='eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ4In0.c2ln'+C
SESSION='{"OPENAI_API_KEY": null, "tokens": {"id_token": "%s", "refresh_token": "rt_%s"}}'%(J,C)
session=[('codex auth.json content',SESSION),('auth.json content, leading newline','\n'+SESSION),('JWT 3-part',J),('JWE 5-part','eyJhbGciOiJkaXIifQ.'+C+'.aXY.Y2lwaGVy.dGFn'),
 ('JWT 2-part unsigned','eyJhbGciOiJub25lIn0.eyJzdWIiOiJ4In0'+C),('Bearer JWT','Bearer '+J),('Bearer=JWT no space','Bearer:'+J),
 ('sk-ant-oat01','sk-ant-oat01-'+C+'A'*40),('sk-ant-ort01','sk-ant-ort01-'+C+'A'*40),('sk-ant-sid01 (claude.ai sessionKey)','sk-ant-sid01-'+C+'A'*40),
 ('cookie sessionKey=','sessionKey=sk-ant-sid01-'+C+'A'*40),('sess-','sess-'+C+'A'*30),('rt_','rt_'+C),('ya29.','ya29.a0'+C+'A'*60),('1//','1//0g'+C+'A'*40),
 ('gho_ (GitHub OAuth)','gho_'+C+'A'*30),('ghu_ (Copilot user token)','ghu_'+C+'A'*30),('copilot session tid=..;exp=..','tid='+C+';exp=1799999999;sku=copilot_for_business'),
 ('next-auth cookie','__Secure-next-auth.session-token='+J),('base64 of session file',base64.b64encode(SESSION.encode()).decode()),
 ('urlsafe-b64 JSON no dots (eyJ...)',base64.urlsafe_b64encode(('{"access_token":"%s"}'%C).encode()).decode().rstrip('=')),
 ('AWS STS session token','IQoJb3JpZ2luX2VjE'+C+'A'*200),('uppercase SESS-','SESS-'+C),('JWT with trailing dot-less sig','eyJ'+C+'.e30.'),
 ('path ~/.codex/auth.json','~/.codex/auth.json'),('path rel .codex/auth.json','.codex/auth.json'),('path rel creds no ext','.claude/.credentials'+C),('win path','C:\\Users\\x\\.codex\\auth'+C),
 ('file: ref','file:~/.codex/auth.json'),('FILE:// ref','FILE:///home/x/a'+C),('@file curl style','@/home/x/auth'+C),('$HOME ref','$HOME/.codex/auth'+C),('env indirection ${VAR}','${OPENAI_API_KEY}'),('path /dev/stdin','/dev/stdin')]
valid=[('anthropic api03','sk-ant-api03-'+C+'-'+'aB3_'*22+'AA'),('openai sk-proj','sk-proj-'+C+'aB3_-'*20),('openai legacy sk-','sk-'+C+'a'*39),('google AIza','AIzaSy'+C+'a'*24),('groq gsk_','gsk_'+C+'a'*47),
 ('xai','xai-'+C+'a'*70),('hf_','hf_'+C+'a'*25),('azure 32 hex','0123456789abcdef0123456789abcd'+C[:2].lower()),('openrouter','sk-or-v1-'+C+'0'*55),('mistral 32','aB3dE'+C+'x'*18),
 ('perplexity','pplx-'+C+'a'*40),('fireworks','fw_'+C+'a'*20),('nvidia','nvapi-'+C+'a_-'*20),('databricks','dapi'+C+'0'*24),('replicate','r8_'+C+'a'*28),('github_pat (PAT)','github_pat_'+C+'a'*60),
 ('base64 key with + / =', C+'aB3+/x9Zq'*8+'=='),('base64 key starting with /','/'+C+'aB3+x9Zq'*8+'='),('aws bedrock api key ABSK','ABSK'+C+'aB3+/'*20+'='),('deepseek','sk-'+C+'0'*23),('key ending in .json?','sk-'+C+'.json'),('litellm sk-1234','sk-1234'),('key eyJ-prefixed opaque no dots','eyJ'+C+'opaquekey')]

from quati.application.providers import key_value_issue
acc=[l for l,v in session if key_value_issue(v) is None]; rej=[l for l,v in valid if key_value_issue(v) is not None]
print('session shapes',len(session),'still accepted:',acc)
print('valid shapes',len(valid),'rejected:',rej)
