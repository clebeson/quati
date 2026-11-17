import json,collections
EV='<local-path>'
d=json.load(open(EV+'SOC-01.json'))
tot=collections.Counter()
for leg in ['a_table_greeting','b_greeting_only_urgency','e_configured_unprobed','e_provider_disabled']:
    L=d['legs'][leg]['records']; bad=[]; per=collections.Counter(); ans=collections.defaultdict(set)
    for r in L:
        resp=r['response']; dt=resp['data']
        ok=(r['exit']==0 and resp['status']=='SUCCEEDED' and dt['result_kind']=='GREETING' and dt['provider_used'] is False and r['provider_used'] is False
            and dt['text_source']=='application_template' and dt['tool_calls']==[] and dt['launched'] is False
            and not any('policy.decided' in json.dumps(a) for a in r.get('audit',[]))
            and r['usage'].get('model_requests',0)==0 and not r['executed'] and dt['actions_taken']==[] and dt['commitment_id'] is None and dt['work_performed'] is False
            and r['receipt']['provider_used'] is False and r['receipt']['result_kind']=='GREETING' and 'synthetic_evidence' not in r['receipt'])
        if not ok: bad.append((r['text'],r['repeat']))
        per[r['text']]+=1; ans[r['text']].add(dt['text'])
    print(leg,len(L),'bad',bad,dict(per)); print('  answers',{k:sorted(v) for k,v in ans.items()})
    print('  states',collections.Counter(r['provider_state'] for r in L), 'audit lens',collections.Counter(len(r.get('audit',[])) for r in L), collections.Counter(len(r.get('audit_events',[])) for r in L))
# print an e unprobed record's audit events
r=d['legs']['e_configured_unprobed']['records'][0]; print(json.dumps(r['audit_events'])[:600], r['provider_state'], json.dumps(r['runtime_identity']['provider']))
r=d['legs']['e_provider_disabled']['records'][0]; print(r['provider_state'], json.dumps(r['runtime_identity']['provider']))
