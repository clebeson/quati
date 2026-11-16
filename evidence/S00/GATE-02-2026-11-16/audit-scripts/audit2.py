import json,hashlib,os,sys,collections
R='/home/clebeson/dev/SECMA/'
E=R+'evidence/S00/T05-20261116T135447Z-claude_cli-haiku-gate6-quati/'
for case,target in (('CAP-01','forecast-lime'),('CAP-02','calendar-read')):
    c=json.load(open(E+case+'.json')); recs=c['records']
    print('==',case)
    r=recs[0]
    for l in r['cli_log']: print('  cli',l['argv'][:4],l['exit'],l['elapsed_s'],repr(l['stderr_tail'][:200]),l['cost_usd'])
    print('  setup',r['setup'])
    cs=collections.Counter(); ex=collections.Counter(); orders=collections.Counter(); first=collections.Counter(); bad=[]; sysh=collections.Counter(); toolsin=collections.Counter()
    desc=collections.Counter(); hashok=collections.Counter(); perm=collections.Counter(); instorder=collections.Counter(); rank_by_seed=[]
    for r in recs:
        se=r['receipt']['synthetic_evidence']; tr=se['trajectory']
        s=tr[0]
        cs[tuple(s['candidate_ids'])]+=1; orders[tuple(s['presented_order'])]+=1
        ex[json.dumps(s.get('excluded'))[:400]]+=1
        instorder[tuple(x[0] for x in r['setup'] if x[0].startswith('install'))]+=1
        desc[tuple(x['arguments'].get('capability_id') for x in tr if x['tool_name']=='quati_describe')]+=1
        # earliest model-visible appearance of the target
        found=None
        for m in se['model_calls']:
            mv=m['model_visible']
            texts=[('system',mv.get('system') or ''),('tsys',(mv.get('transport_rendering') or {}).get('system') or '')]
            for i,msg in enumerate(mv.get('messages') or []):
                texts.append(('msg%d:%s'%(i,msg['role']),msg['content'] if isinstance(msg['content'],str) else json.dumps(msg['content'])))
            for w,t in texts:
                if target in t and found is None:
                    found=(m['index'],m['purpose'],w,t[:60].replace('\n',' '))
            sysh[(m['purpose'],hashlib.sha256((mv.get('system') or '').encode()).hexdigest()[:10])]+=1
            toolsin[(m['purpose'],tuple(mv.get('tool_names') or []))]+=1
        first[found[1:3]+(found[3][:30],) if found else None]+=1
        if found and not found[3].startswith('Tool results'): bad.append((r['utterance_index'],r['repeat'],found))
        # check system prompt & classify call contain no fixture ids at all
        for m in se['model_calls']:
            mv=m['model_visible']
            for t in (mv.get('system') or '', (mv.get('transport_rendering') or {}).get('system') or ''):
                for name in ('forecast-','calendar-read','calendar-write','mail-search','fixtures.'):
                    if name in t: bad.append(('SYSTEM contains',name,r['utterance_index'],r['repeat'],m['index']))
        # receipt hash
        ref=r['response']['evidence_refs'][0].split(':',2)[1]
        cands={
         'sorted-compact':json.dumps(r['receipt'],sort_keys=True,separators=(',',':'),ensure_ascii=False),
         'sorted-indent2':json.dumps(r['receipt'],sort_keys=True,indent=2,ensure_ascii=False),
         'sorted-indent2nl':json.dumps(r['receipt'],sort_keys=True,indent=2,ensure_ascii=False)+'\n',
         'sorted':json.dumps(r['receipt'],sort_keys=True,ensure_ascii=False),
         'sorted-compact-ascii':json.dumps(r['receipt'],sort_keys=True,separators=(',',':')),
         'sorted-indent2-ascii-nl':json.dumps(r['receipt'],sort_keys=True,indent=2)+'\n',
         'sorted-compact-nl':json.dumps(r['receipt'],sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n',
        }
        hit=[k for k,v in cands.items() if hashlib.sha256(v.encode()).hexdigest()==ref]
        hashok[tuple(hit)]+=1
        perm[r['grade']['permutation_seed']]+=1
    print(' candidate_ids',dict(cs)); print(' presented',dict(orders)); print(' excluded',dict(ex)); print(' describe targets',dict(desc))
    print(' install orders',len(instorder)); print(' first appearance of target',dict(first)); print(' bad',bad[:5],len(bad))
    print(' system hashes',dict(sysh)); print(' tools per purpose',dict(toolsin)); print(' receipt hash reproduction',dict(hashok)); print(' distinct perm seeds',len(perm))
    # show one loop call structure
    se=recs[0]['receipt']['synthetic_evidence']
    for m in se['model_calls']:
        mv=m['model_visible']
        print('  call',m['index'],m['purpose'],m['started_at'],m.get('tool_call_names'),[ (x['role'],x['content'][:150].replace('\n','\\n')) for x in mv['messages']][-2:])
    print('  SYSTEM(loop)>>>',se['model_calls'][1]['model_visible']['system'])
    print('  keys rendering',list((se['model_calls'][1]['model_visible'].get('transport_rendering') or {}).keys()))
    print('  STDIN(loop call 2)>>>',se['model_calls'][1]['model_visible']['transport_rendering'].get('stdin')[:3000])
    print('  search result>>>',json.dumps(se['trajectory'][0]['result'])[:2500])
