import json
R='<local-path>'
E=R+'evidence/S00/T05-20261116T135447Z-claude_cli-haiku-gate6-quati/'
for case in ('CAP-01','CAP-02'):
    c=json.load(open(E+case+'.json')); n=0
    for r in c['records']:
        se=r['receipt']['synthetic_evidence']
        if se.get('continuations') or se.get('classification_repairs') or any(m['purpose']=='loop_continuation' for m in se['model_calls']):
            n+=1
            print(case,r['utterance_index'],r['repeat'],'continuations',json.dumps(se.get('continuations'))[:400],'class_repairs',se.get('classification_repairs'),'attempts',se.get('classification_attempts'))
            msgs=se['model_calls'][-1]['model_visible']['messages']
            for i,m in enumerate(msgs):
                if m['role']=='user' and i>0 and not m['content'].startswith('Tool results'): print('    nudge msg%d: %s'%(i,m['content'][:400])); print('    preceding assistant:',msgs[i-1]['content'][:300])
    print(case,'records with continuation/repair',n)
    r=c['records'][0]
    for s in r['receipt']['synthetic_evidence']['trajectory']:
        if s['tool_name']=='quati_describe':
            d=s['result']['data']['definition']; print(case,'describe: desc=',d['description'],'| intents=',d.get('intents'),'| schema=',json.dumps(d['input_schema']))
        if s['tool_name']=='quati_search': print(case,'search data',json.dumps(s['result']['data'])[:1300]); print(' rank_reasons',json.dumps(s.get('rank_reasons'))[:700])
    print(case,'catalog',json.dumps(r['receipt']['synthetic_evidence'].get('catalog'))[:1500])
