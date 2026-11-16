import json
R='<local-path>'
E=R+'evidence/S00/T05-20261116T135447Z-claude_cli-haiku-gate6-quati/'
E2=R+'evidence/S00/T05-20261116T142110Z-claude_cli-haiku-gate6b-beh-quati/'
suite=json.load(open(R+'tests/evals/datasets/behavior_suite.json'))
print({k:v for k,v in suite.items() if k!='cases'})
cs={c['id']:c for c in suite['cases']}
a=json.load(open(E+'BEH.json')); b=json.load(open(E2+'BEH.json'))
for cid in ('BEH-02','BEH-10','BEH-13','BEH-09'):
    print('#####',cid,json.dumps(cs[cid],ensure_ascii=False))
    for name,c in (('gate6',a),('gate6b',b)):
        r=[x for x in c['records'] if x['case_id']==cid][0]
        v=r['response']; rc=r['receipt'] or {}; se=rc.get('synthetic_evidence') or {}
        print(' --',name,'exit',r['exit'],'grade',r['grade'],'judge',r['judge'])
        print('    status',v.get('status'),'error',v.get('error'),'unc',v.get('uncertainties'),'next',v.get('next_action'))
        d=v.get('data') or {}
        print('    data',json.dumps({k:d.get(k) for k in ('result_kind','reason','provider_used','feature_support','text','delivered','launched','classification')},ensure_ascii=False)[:700])
        print('    setup',[(s[0],s[1],s[2],(json.dumps(s[3])[:500] if len(s)>3 else '')) for s in r['setup'][:2]])
        print('    cli',[(l['argv'][:2],l['exit'],l['elapsed_s'],l['stderr_tail'][:200]) for l in r['cli_log']])
        print('    calls',[(m['purpose'],m['outcome'],m['started_at'][11:23],m['ended_at'][11:23],m.get('stop_reason')) for m in se.get('model_calls') or []])
        print('    final',repr(se.get('final_model_text'))[:400],'outcome',se.get('outcome'))
        if not se: print('    receipt',json.dumps(rc)[:900])
# all provider-failed timestamps in gate6
print('#### outage timeline gate6')
for r in a['records']:
    se=(r['receipt'] or {}).get('synthetic_evidence') or {}
    for m in se.get('model_calls') or []:
        if m['outcome']!='OK': print(r['case_id'],m['purpose'],m['outcome'],m['started_at'],m['ended_at'],{k:v for k,v in m.items() if k not in('model_visible','usage','started_at','ended_at')})
# last OK call across the gate6 run
import glob
last=''
for r in a['records']:
    for m in ((r['receipt'] or {}).get('synthetic_evidence') or {}).get('model_calls') or []:
        if m['outcome']=='OK': last=max(last,m['ended_at'])
print('last OK call end',last)
pa=json.load(open(E+'PREREG.json')); pb=json.load(open(E2+'PREREG.json'))
print('prereg equal except run_id',{k:pa[k]==pb[k] for k in pa})
ia=json.load(open(E+'INDEX.json')); ib=json.load(open(E2+'INDEX.json'))
print('gate6 BEH summary',json.dumps(ia['summary']['BEH'])[:300]); print('gate6b INDEX',json.dumps({k:v for k,v in ib.items() if k!='summary'})); print(json.dumps(ib['summary'])[:600])
CONST=['behavior_hash','behavior_prompt_hash','catalog_digest','code_digest','config_hash','model_digest','statechart_hash','tool_schema_digest']
c1=json.load(open(E+'CAP-01.json'))
print('const digests gate6 CAP-01 vs gate6 BEH vs gate6b BEH',{k:(c1['digests'][k]==a['digests'][k] if k!='catalog_digest' else None, a['digests'][k]==b['digests'][k]) for k in CONST})
