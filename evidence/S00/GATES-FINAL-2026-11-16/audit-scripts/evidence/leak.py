import json,re
G='<local-path>'
idx=json.load(open(G+'INDEX.json'))
print({k:(v if len(json.dumps(v))<300 else '...') for k,v in idx.items() if 'cost' in k or 'total' in k})
for case,names in (('CAP-01',['forecast-lime','forecast_lime','lime']),('CAP-02',['calendar-read','calendar_read','calendar-write','mail-search'])):
    d=json.load(open(G+case+'.json')); recs=d['records']
    ut=set(r['utterance'] for r in recs)
    print(case,'utterance hits',[(u,n) for u in ut for n in names if n.lower() in u.lower()])
    first=0;sysh=0;pre=0
    for r in recs:
        mc=r['receipt']['synthetic_evidence']['model_calls']
        for i,c in enumerate(mc):
            mv=c['model_visible']; s=json.dumps(mv).lower()
            # model-visible content of the very first call and system prompts
            if i==0 and any(n in s for n in names): first+=1
            sy=json.dumps(mv.get('system','')).lower()
            if any(n in sy for n in names): sysh+=1
    print(case,'first-call hits',first,'system hits',sysh,'keys',list(mc[0]['model_visible'].keys()))
    # first appearance index of target in messages
    firstidx=collections=None
for case,tgt in (('CAP-01','forecast-lime'),('CAP-02','calendar-read')):
    d=json.load(open(G+case+'.json')); recs=d['records']; pos=[]
    for r in recs:
        mc=r['receipt']['synthetic_evidence']['model_calls']
        pos.append(next((i for i,c in enumerate(mc) if tgt in json.dumps(c['model_visible'])),None))
    import collections as C; print(case,'first model call index mentioning',tgt,C.Counter(pos))
