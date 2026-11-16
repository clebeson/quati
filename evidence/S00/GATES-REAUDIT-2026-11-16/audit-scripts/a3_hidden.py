from h import *
P='g3'
def tc(script,text='Publish the forecast and update my calendar'):
    n0=len(audit(P)); s0=len(spy(P)); c,o,e=model2(P,script,'ask','--json','--',text); v=json.loads(o); d=v['data']
    print('  exit',c,v['status'],(v.get('error') or {}).get('code'),d.get('reason'),[(t['operation'],t['status'],t['reason'],t.get('policy_verdict')) for t in d['tool_calls']],'handlers',[x for x in spy(P)[s0:] if x[0]=='handler'],'audit+',[(a['event'],(a.get('decision') or {}).get('verdict') if a['event']=='authz.decided' else a.get('verdict') or a.get('reason')) for a in audit(P)[n0:] if a['event']!='authz.decided'])
for cid in ('fixtures.forecast-publish','fixtures.calendar-write','fixtures.does-not-exist','fixtures.mail-search'):
    print(cid); tc([['classify'],['search','publish forecast'],['describe',cid],['invoke',cid,{'region':'north','weeks':4}],['final','Published.']])
    print('   operator describe:',one(q(P,'capabilities','describe',cid,'--json')))
print('search results for write query:'); c,o,e=q(P,'capabilities','search','publish forecast write calendar event','--json'); print('  ',[x.get('capability_id') for x in json.loads(o)['data'].get('candidates',json.loads(o)['data'].get('results',[]))], list(json.loads(o)['data'])[:8])
