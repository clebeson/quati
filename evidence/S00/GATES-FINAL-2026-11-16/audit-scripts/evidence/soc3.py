import json,collections
EV='<local-path>'
d=json.load(open(EV+'SOC-01.json'))
print(list(d['legs'].keys()), [k for k in d if k!='legs'])
for leg,L in d['legs'].items():
    if not any(leg.startswith(p) for p in('c_','d_','h_','chat','g_','f_')): continue
    recs=L.get('records',[])
    print('==',leg,len(recs),[k for k in L if k!='records'])
    by=collections.defaultdict(list)
    bad=[]
    for r in recs:
        resp=r['response']; st=resp.get('status'); ex=r['exit']
        by[r['text']].append((ex,st,r['outcome'],tuple(r['executed'])))
        if r['executed'] or r.get('read_executed'): bad.append(('exec',r['text']))
        if st=='SUCCEEDED' and not r['executed'] and resp['data'].get('result_kind')!='GREETING': bad.append(('succ_noexec',r['text']))
        if st=='SUCCEEDED' and leg.startswith(('c_','d_','h_')): bad.append(('succ',r['text']))
        s=json.dumps(resp)
        if resp['data'].get('commitment_id'): bad.append(('commit',r['text']))
    for t,v in by.items(): print(' ',repr(t)[:60],len(v),collections.Counter((a,b,c) for a,b,c,_ in v).most_common(3))
    print(' bad',bad)
    if 'chat' in leg: print(json.dumps(L)[:1500])
