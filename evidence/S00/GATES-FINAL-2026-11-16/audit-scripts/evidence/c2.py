import json,collections
EV='<local-path>'
for case in ['CAP-01','CAP-02']:
    d=json.load(open(EV+case+'.json'))
    for r in d['records']:
        se=r['receipt']['synthetic_evidence']
        if se['continuations'] or r['receipt']['continuations'] or len(se['model_calls'])!=5:
            print(case,r['utterance_index'],r['repeat'],'cont',json.dumps(se['continuations']),json.dumps(r['receipt']['continuations']),len(se['model_calls']),r['response']['data']['usage'])
            for m in se['model_calls']: print('  mc',m['index'],m.get('kind'),[k for k in m if k not in('model_visible',)], json.dumps(m['model_visible'])[-600:] if m['index']>=5 else '')
    # candidates lists for trace explain
    if case=='CAP-02':
        cnt=collections.Counter()
        for r in d['records']:
            te=r['trace_explain']; 
            lc=te['listed_candidates']
            cnt[json.dumps(lc,sort_keys=True)]+=1
            # alternatives
        print(cnt)
        te=d['records'][0]['trace_explain']
        print(json.dumps(te['response']['data'],indent=1)[:6000])
