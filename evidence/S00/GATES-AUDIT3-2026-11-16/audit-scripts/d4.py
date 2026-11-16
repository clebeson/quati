from h import *
import json, re, glob
ready('d4')
for f in ('calendar-write','forecast-publish','mail-search'):
    r=q('d4','capabilities','install-fixture',f,'--json'); print('install',f,r[0],brief(r[1])[0]['status'],brief(r[1])[0]['reason'])
r=q('d4','capabilities','list','--json'); print([(c['capability_id'],c['lifecycle']) for c in json.loads(r[1])['data']['capabilities']])
ids=['fixtures.calendar-write','fixtures.forecast-publish','fixtures.mail-search','fixtures.does-not-exist','NOT A VALID ID !!','fixtures.calendar-read']
script=[['classify'],['search','zzzz qqqq nothing']]
for i in ids[:5]: script += [['describe',i]]
script += [['final','x'],['final','y']]
before=len(audit('d4'))
r=model('d4',script,'ask','please publish the forecast','--json','--synthetic-evidence')
v=json.loads(r[1]); print(r[0], v['status'], v['data']['reason'])
rec=json.loads(open(v['evidence_refs'][0].split(':',2)[2]).read())
for st in rec['synthetic_evidence']['trajectory']:
    res=st['result']; print(' ',st['operation'],st['status'],st['reason'],st['capability_ref'][:20] if st['capability_ref'] else None, json.dumps({k:res[k] for k in res if k not in('notice',)},sort_keys=True)[:230])
print('audit new:',[ (e['event'], e.get('operation'), e.get('capability_id'), e.get('reason')) for e in audit('d4')[before:]])
script=[['classify'],['search','zzzz qqqq nothing']]
for i in ids[:5]: script += [['invoke',i,{}]]
script += [['final','x'],['final','y']]
before=len(audit('d4'))
r=model('d4',script,'ask','please publish the forecast','--json','--synthetic-evidence')
v=json.loads(r[1]); print(r[0], v['status'], v['data']['reason'], 'handlers',[x for x in r[3] if x[0]=='handler'])
print(' tool_calls:', [(t['operation'],t['status'],t['reason'],str(t['capability_ref'])[:16]) for t in v['data']['tool_calls']])
rec=json.loads(open(v['evidence_refs'][0].split(':',2)[2]).read())
outs=[]
for st in rec['synthetic_evidence']['trajectory']:
    res=st['result']; outs.append(json.dumps(res,sort_keys=True))
    print(' ',st['operation'],st['status'],st['reason'], st['selection_error'], st['policy_verdict'])
print(' invoke results identical text for hidden/unknown/malformed:', len(set(outs[1:]))==1)
print('audit new:',[ (e['event'], e.get('operation'), e.get('capability_id'), e.get('reason')) for e in audit('d4')[before:]])
# operator path
for i in ids:
    r=q('d4','capabilities','describe',i,'--json'); b=brief(r[1])[0]; print('operator describe',i,r[0],b['status'],b['code'],b['reason'])
# write attempt on public path: search for write words, try to invoke write fixture
script=[['classify'],['search','calendar write create event'],['describe','fixtures.calendar-write'],['invoke','fixtures.calendar-write',{'title':'x'}],['final','done']]
before=len(audit('d4'))
r=model('d4',script,'ask','Create a calendar event tomorrow 9am','--json','--synthetic-evidence')
v=json.loads(r[1]); print(r[0], v['status'], v['error'], v['data']['reason'], 'handlers',[x for x in r[3] if x[0]=='handler'], 'launched', v['data']['launched'])
print(' tool_calls:', [(t['operation'],t['status'],t['reason']) for t in v['data']['tool_calls']])
print('audit new:',[ (e['event'], e.get('operation'), e.get('capability_id'), e.get('reason'), (e.get('decision') or {}).get('verdict')) for e in audit('d4')[before:]])
