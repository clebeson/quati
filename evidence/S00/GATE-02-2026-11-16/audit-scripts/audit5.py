import json,os,glob,re
R='<local-path>'
S=R+'evidence/S00/'
for d in sorted(os.listdir(S)):
    p=S+d
    if not os.path.isdir(p) or not d.startswith('T05'): continue
    try:
        idx=json.load(open(p+'/INDEX.json'))
    except Exception as e: print(d,'no index'); continue
    pre=json.load(open(p+'/PREREG.json')) if os.path.exists(p+'/PREREG.json') else {}
    sm=idx.get('summary',{})
    print(d[4:], 'runs',idx.get('runs_per_utterance'), {k:(v.get('passed'),v.get('n')) if 'n' in v else v.get('pass') for k,v in sm.items()}, 'ds',{k[:5]:v[:8] for k,v in (pre.get('datasets') or {}).items()}, 'code',(pre.get('code_digest_src_quati') or '')[:8])
E=S+'T05-20261116T135447Z-claude_cli-haiku-gate6-quati/'
for case,target in (('CAP-01','fixtures.forecast-lime'),('CAP-02','fixtures.calendar-read')):
    c=json.load(open(E+case+'.json'))
    for r in c['records']:
        se=r['receipt']['synthetic_evidence']
        pur=[m['purpose'] for m in se['model_calls']]
        if 'loop_continuation' in pur or len(pur)!=5:
            print(case,r['utterance_index'],r['repeat'],pur,[m.get('tool_call_names') for m in se['model_calls']],[m.get('stop_reason') for m in se['model_calls']])
            last=se['model_calls'][-1]['model_visible']['messages']
            for m in last[1:]: print('     ',m['role'],m['content'][:330].replace('\n','\\n'))
    r=c['records'][0]; se=r['receipt']['synthetic_evidence']
    print(case,'se keys',sorted(se.keys())); print(' provider',se['provider'])
    for s in se['trajectory']:
        if s['tool_name']=='quati_describe': print(' describe result',json.dumps(s['result'])[:1500])
        if s['tool_name']=='quati_invoke': print(' invoke step',json.dumps({k:v for k,v in s.items() if k not in('result','context')})[:900])
    print(' search cands',json.dumps(se['trajectory'][0]['result']['data'])[:1200])
    print(' receipt non-se',json.dumps({k:v for k,v in r['receipt'].items() if k not in('synthetic_evidence','digests')})[:900])
t=open(E+'CAP-01.json').read()
print('cli version mentions',set(re.findall(r'"[a-z_]*version[a-z_]*": "[^"]{1,40}"',t)))
