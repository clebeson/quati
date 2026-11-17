from h import *
import json, os
ready('ms')
for cmd in (('server',),('spaces','describe','x'),('policy','apply','f'),('login',),('grants','list'),('worker','run'),('trace','export','x'),('config','diff'),('behavior','promote','x'),('memory','search','q'),('nonexistent',),('ask',),('ask','')):
    r=q('ms',*cmd,'--json'); v=json.loads(r[1].splitlines()[-1]); print(cmd, r[0], v['status'], v['error']['code'], (v['error']['message'] or '')[:50])
# unauthenticated UNSUPPORTED (audit-1 finding 13 debt)
fresh('ms0'); r=q('ms0','server','--json'); print('uninit server', r[0], json.loads(r[1])['error']['code'])
# empty model reply
for script in ([['classify_social'],['final','']],[['classify'],['final',''],['final','']]):
    r=model('ms',script,'ask','Tell me a joke','--json'); v=json.loads(r[1]); print('empty reply', r[0], v['status'], (v['error'] or {}).get('code'), v['data']['reason'], v['data']['launched'])
# corrupted audit line: reads and writes alike
ap=root('ms')/'data/capabilities/audit.jsonl'; orig=ap.read_bytes(); ap.write_bytes(orig+b'{"torn":\n')
READ=[['classify'],['search','next appointment calendar'],['describe','fixtures.calendar-read'],['invoke','fixtures.calendar-read',{'limit':1}],['final','done']]
for label,fn in (('list',lambda: q('ms','capabilities','list','--json')+([],)),('disable',lambda: q('ms','capabilities','disable','fixtures.calendar-read@1.0.0','--json')+([],)),('ask read',lambda: model('ms',READ,'ask','Find my next appointment','--json')),('greet',lambda: q('ms','ask','hello','--json')+([],)),('probe',lambda: model('ms',[],'models','probe','--json'))):
    r=fn(); v=json.loads(r[1]); print('torn audit:',label,r[0],v['status'],(v['error'] or {}).get('code'),(v['data'] or {}).get('reason'),'spy',[x[0] for x in r[3] if x[0]!='script_left'])
ap.write_bytes(orig)
# oversized / control input
big='hello '*11000
r=q('ms','ask',big,'--json'); print('66k greeting', r[0], json.loads(r[1])['error']['code'])
r=q('ms','ask','hello\x00delete','--json') if False else None
r=q('ms','chat','--jsonl',stdin=b'hello\n/approve apr-1\nhello /approve x\n\xff\xfe\n'); print('chat lines', r[0], [ (json.loads(l)['status'], (json.loads(l)['error'] or {}).get('code'), (json.loads(l)['data'] or {}).get('result_kind') or (json.loads(l)['data'] or {}).get('reason')) for l in r[1].splitlines()])
