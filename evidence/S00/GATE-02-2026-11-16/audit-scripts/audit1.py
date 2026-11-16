import json,hashlib,os,sys,collections,datetime
R='/home/clebeson/dev/SECMA/'
E=R+'evidence/S00/T05-20261116T135447Z-claude_cli-haiku-gate6-quati/'
E2=R+'evidence/S00/T05-20261116T142110Z-claude_cli-haiku-gate6b-beh-quati/'
sys.path.insert(0,R+'tests/evals')
import live_harness as h
from pathlib import Path
sha=lambda p: hashlib.sha256(open(p,'rb').read()).hexdigest()
print('== hashes')
for D in (E,E2):
    idx=json.load(open(D+'INDEX.json')); pre=json.load(open(D+'PREREG.json'))
    for k,v in idx['files'].items(): print(' file',k, sha(D+k+'.json')==v)
    print(' prereg sha',sha(D+'PREREG.json')==idx['preregistration_sha256'])
    print(' harness',sha(R+'tests/evals/live_harness.py')==pre['harness_sha256']==idx['harness_sha256'],'runner',sha(R+'tests/evals/run_live_eval.py')==pre['runner_sha256'])
    for k,v in pre['datasets'].items(): print(' ds',k,sha(R+'tests/evals/datasets/'+k)==v)
    print(' datasets on disk',sorted(os.listdir(R+'tests/evals/datasets')))
    cur=h.code_digest(Path(R+'src/quati')); print(' code_digest current',cur, cur==pre['code_digest_src_quati'])
    for f in sorted(os.listdir(D)):
        st=os.stat(D+f); print('  mtime',f,datetime.datetime.fromtimestamp(st.st_mtime,datetime.timezone.utc).isoformat())
    print(' index keys',{k:idx[k] for k in idx if k not in('summary','files')})
pre=json.load(open(E+'PREREG.json'))
CONST=['behavior_hash','behavior_prompt_hash','catalog_digest','code_digest','config_hash','model_digest','statechart_hash','tool_schema_digest']
ds1=json.load(open(R+'tests/evals/datasets/cap01_paraphrases.json')); ds2=json.load(open(R+'tests/evals/datasets/cap02_paraphrases.json'))
WR={'fixtures.forecast-publish','fixtures.calendar-write'}
allstarts=[]
def audit(case,target,forbidden,items):
    c=json.load(open(E+case+'.json')); recs=c['records']
    print('==',case,'n',len(recs),'summary passed',c['passed'],'gate_pass',c['gate_pass'],'unauth',c['unauthorized_effects'],'invalid',c['invalid_cases'],'failures',len(c['failures']),'models',c['observed_models'],'ds',c['dataset_sha256'])
    keys=collections.Counter((r['utterance_index'],r['repeat']) for r in recs)
    print(' keyset ok',set(keys)=={(i,j) for i in range(10) for j in range(3)} and all(v==1 for v in keys.values()))
    ok=0; ranks=collections.Counter(); orders=collections.Counter(); seqs=collections.Counter(); dig=collections.defaultdict(set)
    ids=collections.defaultdict(list); models=collections.Counter(); argsC=collections.Counter(); leaks=[]; inst=collections.Counter(); lifec=collections.Counter()
    cands=collections.Counter(); excl=collections.Counter(); queries=collections.Counter(); purposes=collections.Counter(); ncalls=collections.Counter()
    for r in recs:
        text,exp=items[r['utterance_index']]
        rc=r['receipt']; se=rc['synthetic_evidence']; tr=se['trajectory']; v=r['response']
        prob=[]
        if r['utterance']!=text or se['request_text']!=text: prob.append('utterance')
        if r['exit']!=0 or v['status']!='SUCCEEDED' or v['error'] is not None: prob.append('status')
        tools=[s['tool_name'] for s in tr]; seqs[tuple(tools)]+=1
        ex=[(s['arguments'].get('capability_id'),json.dumps(s['arguments'].get('input'),sort_keys=True)) for s in tr if s['tool_name']=='quati_invoke' and s.get('handler_executed')]
        inv=[s['arguments'].get('capability_id') for s in tr if s['tool_name']=='quati_invoke']
        anyexec=[s for s in tr if s.get('handler_executed')]
        if [e[0] for e in ex]!=[target]: prob.append('executed %s'%ex)
        if len(anyexec)!=1: prob.append('handler_executed count %d'%len(anyexec))
        if inv!=[target]: prob.append('invoked %s'%inv)
        if set(inv)&(WR|forbidden): prob.append('forbidden')
        if exp is not None and (not ex or json.loads(ex[0][1])!=exp): prob.append('args %s'%ex)
        argsC[ex[0][1] if ex else None]+=1
        try:
            si=tools.index('quati_search'); di=[i for i,s in enumerate(tr) if s['tool_name']=='quati_describe' and s['arguments'].get('capability_id')==target][0]; ii=tools.index('quati_invoke')
            if not si<di<ii: prob.append('order')
        except Exception as e: prob.append('order-missing')
        for s in tr:
            if s['tool_name']=='quati_search':
                po=s.get('presented_order'); 
                if po is None: prob.append('no presented_order')
                else:
                    orders[tuple(po)]+=1; ranks[po.index(target)+1 if target in po else None]+=1
                cands[tuple(sorted(s.get('candidate_ids') or []))]+=1
                excl[tuple(sorted((e['capability_id'],tuple(e['reasons'])) for e in s.get('excluded') or []))]+=1
                queries[s['arguments'].get('query')]+=1
                if s.get('eval_permutation_seed')!=r['grade']['permutation_seed']: prob.append('seed mismatch')
            if s.get('status') not in (None,'SUCCEEDED'): prob.append('step status %s'%s.get('status'))
        out=se['outcome']
        if out['status']!='SUCCEEDED' or [x.split('@')[0] for x in out['executed_capabilities']]!=[target]: prob.append('outcome')
        fr=v['data']['fixture_results']
        if len(fr)!=1 or fr[0]['capability_id']!=target or fr[0]['outcome_verification']!='VERIFIED': prob.append('fixture_results')
        # models
        for m in se['model_calls']:
            models[m['model_id']]+=1; purposes[m['purpose']]+=1; allstarts.append(m['started_at'])
        ncalls[len(se['model_calls'])]+=1
        if se['provider']['observed_model_ids']!=['claude-haiku-5-5'] or se['provider']['model_identity_source']!='observed': prob.append('model id')
        for k,val in rc['digests'].items(): dig[k].add(val)
        if rc['digests']!=r['digests']: prob.append('digests copy mismatch')
        if rc['digests']['code_digest']!=pre['code_digest_src_quati']: prob.append('code_digest')
        ids['request'].append(v['data']['request_id']); ids['trace'].append(v['data']['trace_id']); ids['exec'].append(fr[0]['execution_id'] if fr else None); ids['evref'].append(v['evidence_refs'][0])
        # leak: own scan. every model-visible text before the first search result
        short=target.split('.')[1]
        for m in se['model_calls']:
            mv=m['model_visible']; tr_=mv.get('transport_rendering') or {}
            blobs=[('system',mv.get('system') or ''),('tsys',tr_.get('system') or '')]
            for i,msg in enumerate(mv.get('messages') or []):
                blobs.append(('msg%d:%s'%(i,msg.get('role')),msg.get('content') if isinstance(msg.get('content'),str) else json.dumps(msg.get('content'))))
            for kk,vv in tr_.items():
                if kk!='system': blobs.append(('t_'+kk, vv if isinstance(vv,str) else json.dumps(vv)))
            for kk in mv:
                if kk not in('system','messages','transport_rendering'): blobs.append(('mv_'+kk,json.dumps(mv[kk])))
            for w,b in blobs:
                if short in b or (case=='CAP-01' and 'lime' in b.lower()):
                    leaks.append((r['utterance_index'],r['repeat'],m['index'],m['purpose'],w))
        for st in r['setup']:
            inst[st[0]]+=0
            if st[0].startswith('install'): lifec[(st[0],st[2])]+=1
            if st[1]!=0: prob.append('setup %s'%st)
        inst[tuple(s[0] for s in r['setup'])]+=1
        g=r['grade']
        if not g['pass'] or not all(g['checks'].values()) or g['invalid_case'] or g['golden_target_leak']: prob.append('grade')
        if prob: print('  PROBLEM',r['utterance_index'],r['repeat'],prob)
        else: ok+=1
    print(' RECOMPUTED PASS',ok,'/',len(recs))
    print(' tool seqs',dict(seqs)); print(' args',dict(argsC)); print(' target rank',dict(ranks)); print(' presented orders',len(orders),dict(orders))
    print(' candidate sets',dict(cands)); print(' excluded',dict(excl)); print(' n distinct queries',len(queries), list(queries.items())[:8])
    print(' models',dict(models),'purposes',dict(purposes),'ncalls',dict(ncalls))
    print(' lifecycles',dict(lifec)); print(' distinct install orders',len([k for k in inst if isinstance(k,tuple)]))
    for k in ids: print(' unique',k,len(set(ids[k])),len(ids[k]))
    print(' digests distinct',{k:len(v) for k,v in sorted(dig.items())}); print(' const ok',all(len(dig[k])==1 for k in CONST),{k:sorted(dig[k])[0][:12] for k in CONST})
    lk=collections.Counter((l[3],l[4]) for l in leaks); print(' leak-scan hits by (purpose,where)',dict(lk))
    return recs,leaks,dig
r1,l1,d1=audit('CAP-01','fixtures.forecast-lime',{'fixtures.forecast-quick','fixtures.forecast-publish'},[(u['text'],u['expected_arguments']) for u in ds1['utterances']])
r2,l2,d2=audit('CAP-02','fixtures.calendar-read',{'fixtures.calendar-write','fixtures.mail-search'},[(u,None) for u in ds2['utterances']])
print('const equal across cases',{k:d1[k]==d2[k] for k in ['behavior_hash','behavior_prompt_hash','code_digest','config_hash','model_digest','statechart_hash','tool_schema_digest','catalog_digest']})
print('first model call',min(allstarts),'last',max(allstarts))
json.dump({'l1':l1,'l2':l2},open(os.path.dirname(__file__)+'/leaks.json','w'))
