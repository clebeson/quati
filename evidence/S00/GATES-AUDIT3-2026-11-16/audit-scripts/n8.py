import sys, base64, json, binascii, urllib.parse, gzip
sys.path.insert(0,'<local-path>')
from quati.application.providers import key_value_issue
C='CANARY7x9'
J='eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ4In0.c2ln'+C
SESSION='{"OPENAI_API_KEY": null, "tokens": {"id_token": "%s", "refresh_token": "rt_%s"}}'%(J,C)
new=[('padded JWT (= padding)','eyJhbGciOiJSUzI1NiJ9==.eyJzdWIiOiJ4In0=.c2ln'),('JWT std-b64 chars +/', 'eyJhbGci+iJSUzI1NiJ9.eyJzdWIi/iJ4In0.c2ln'),
 ('JWT with prefix token:', 'token:'+J),('access_token:JWT','access_token:'+J),('Authorization:Bearer<jwt> nospace','Authorization:Bearer'+J),('quoted JWT','"'+J+'"'),("single-quoted JWT","'"+J+"'"),
 ('JWT trailing comma', J+','),('JWT uppercase EYJ', 'EYJ'+J[3:]),('two JWTs joined by |', J+'|'+J),('JWT + #frag', J+'#x'),
 ('uppercase SK-ANT-OAT01','SK-ANT-OAT01-'+C+'A'*40),('sk-ant-oat (no digits)','sk-ant-oat-'+C+'A'*40),
 ('slack xoxc session','xoxc-'+C+'-1234567890-abcdef'),('slack xoxd cookie','xoxd-'+C+'%2Babc'),('hf oauth','hf_oauth_'+C+'a'*30),
 ('hex of session file', binascii.hexlify(SESSION.encode()).decode()),('urlencoded session JSON', urllib.parse.quote(SESSION)),
 ('gzip+b64 session', base64.b64encode(gzip.compress(SESSION.encode())).decode()),('b64 of b64 session', base64.b64encode(base64.b64encode(SESSION.encode())).decode()),
 ('b64 session w/o padding', base64.b64encode(SESSION.encode()).decode().rstrip('=')),('b64url session', base64.urlsafe_b64encode(SESSION.encode()).decode()),
 ('b64 of " {json}" leading space', base64.b64encode((' '+SESSION).encode()).decode()),('b64 of JSON array', base64.b64encode(('['+SESSION+']').encode()).decode()),
 ('b64 of yaml-ish creds', base64.b64encode(b'access_token: abc\nrefresh_token: def\n').decode()),
 ('relative path no dot-slash creds/auth', 'creds/auth'),('path with backslash rel', 'creds\\auth'),('home var %USERPROFILE%', '%USERPROFILE%\\.codex\\auth'),('tilde user', '~root/.codex/auth'),
 ('op:// ref', 'op://vault/item/key'),('env:VAR', 'env:OPENAI_API_KEY'),('$VAR', '$OPENAI_API_KEY'),('keyring:', 'keyring:quati/openai'),('vault:', 'vault:secret/data/x#key'),
 ('aws AKIA access key id', 'AKIAIOSFODNN7EXAMPLE'),('aws ASIA temp id', 'ASIAIOSFODNN7EXAMPLE'),('gcp service acct json b64', base64.b64encode(b'{"type":"service_account","private_key":"x"}').decode()),
 ('PEM one-line', '-----BEGINPRIVATEKEY-----MIIEv'),('codex id_token only refresh rt.', 'rt.'+C),('oauth "v1." refresh', 'v1.'+C+'M'*40),
 ('claude session cookie value no prefix', 'sk-ant-sid02-'+C+'A'*40),('openai sess- uppercase mixed', 'SeSs-'+C+'A'*30),('ghs_ (GitHub app install)', 'ghs_'+C+'A'*30),('ghr_ refresh', 'ghr_'+C+'A'*30),
 ('gcloud ya29 uppercase', 'YA29.a0'+C),('AWS STS FwoGZX', 'FwoGZXIvYXdzE'+C+'A'*200),('empty', ''),('one char','x'),('nbsp inside', 'sk-abc def'),('zero-width inside', 'sk-abc​def'),('unicode key', 'sk-ключ'+C)]
for label,val in new:
    print(f'{label:42} -> {key_value_issue(val)!r}')
