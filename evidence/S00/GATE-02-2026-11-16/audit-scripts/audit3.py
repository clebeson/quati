import json,hashlib,os,sys,collections,re
R='/home/clebeson/dev/SECMA/'
E=R+'evidence/S00/T05-20261116T135447Z-claude_cli-haiku-gate6-quati/'
E2=R+'evidence/S00/T05-20261116T142110Z-claude_cli-haiku-gate6b-beh-quati/'
PRE=json.load(open(E+'PREREG.json'))['code_digest_src_quati']
def traj(rc): return ((rc or {}).get('synthetic_evidence') or {}).get('trajectory') or []
def calls(rc): return ((rc or {}).get('synthetic_evidence') or {}).get('model_calls') or []
def brief(v):
    d=v.get('data') or {}
    return dict(status=v.get('status'),error=(v.get('error') or {}).get('code') if isinstance(v.get('error'),dict) else v.get('error'),kind=d.get('result_kind'),reason=d.get('reason'),provider_used=d.get('provider_used'),commit=d.get('commitment_id'),fs=d.get('feature_support'),text=(d.get('text') or '')[:260])
print('== CAP-03'); c=json.load(open(E+'CAP-03.json'))
print(c['pass'],c['checks'],c['setup'][-4:]); print(brief(c['response'])); print('error',json.dumps(c['response'].get('error'))[:400])
rc=c['receipt']
for s in traj(rc): print('  step',s['tool_name'],json.dumps(s['arguments'])[:120],'exec',s.get('handler_executed'),'cands',s.get('candidate_ids'),'excl',json.dumps(s.get('excluded'))[:300],'reason',s.get('reason'), (s.get('result') or {}).get('status'))
print('  calls',[(m['purpose'],m['model_id'],m['outcome'],m['started_at']) for m in calls(rc)])
print('  final',((rc or {}).get('synthetic_evidence') or {}).get('final_model_text'))
print('  code',(rc or {}).get('digests',{}).get('code_digest')==PRE, 'outcome',((rc or {}).get('synthetic_evidence') or {}).get('outcome'))
print('  cli',[(l['argv'][:3],l['exit']) for l in c['cli_log']])
print('== CAP-05'); c=json.load(open(E+'CAP-05.json'))
print(c['pass'],c['checks'],c['setup']); print(json.dumps(c['response'])[:1500]); print('receipt?',c['receipt'] is not None, 'traj',len(traj(c['receipt'])),'calls',len(calls(c['receipt'])))
if c['receipt']: print('  receipt keys',list(c['receipt'].keys()), json.dumps({k:v for k,v in c['receipt'].items() if k!='synthetic_evidence'})[:800]); print('  se outcome',(c['receipt'].get('synthetic_evidence') or {}).get('outcome'),(c['receipt'].get('synthetic_evidence') or {}).get('provider'))
print('  cli',[(l['argv'][:3],l['exit'],l['elapsed_s'],l['cost_usd']) for l in c['cli_log']])
print('== SOC-01'); c=json.load(open(E+'SOC-01.json'))
print(c['pass'],c['l3_runs'],c['setup'][:1], [s[:3] for s in c['setup'][1:]])
for r in c['results']:
    rc=r['receipt']
    print(' ',r['text'],'|',r['tier_claim'],r['pass'],r['checks']); print('    ',brief(r['response']))
    print('     traj',len(traj(rc)),'tool_calls',(r['response'].get('data') or {}).get('tool_calls'),'calls',[(m['purpose'],m['model_id'],m['outcome'],m.get('tool_call_names')) for m in calls(rc)],'code',(rc or {}).get('digests',{}).get('code_digest')==PRE,'obs',((rc or {}).get('synthetic_evidence') or {}).get('provider',{}).get('observed_model_ids'))
suite=json.load(open(R+'tests/evals/datasets/behavior_suite.json'))
for D in (E,E2):
    print('== BEH',D[-30:]); c=json.load(open(D+'BEH.json'))
    print(' n',c['n'],'passed',c['passed'],'models',c['observed_models'],'unauth',c['unauthorized_effects'],'distinct',c['distinct_digest_values'])
    print(' order matches suite',[r['case_id'] for r in c['records']]==[x['id'] for x in suite['cases']], all(r['utterance']==x['text'] for r,x in zip(c['records'],suite['cases'])))
    for r in c['records']:
        rc=r['receipt']; v=r['response']; b=brief(v)
        ex=[(s['arguments'].get('capability_id'),json.dumps(s['arguments'].get('input'))) for s in traj(rc) if s.get('handler_executed')]
        st=[m['started_at'][11:19] for m in calls(rc)]
        print('  %-28s pass=%s exit=%s %s/%s kind=%s exec=%s tools=%s calls=%s code_ok=%s judge=%s el=%s'%(r['case_id'],r['grade']['pass'],r['exit'],b['status'],b['error'],b['kind'],ex,[s['tool_name'] for s in traj(rc)],(st[0],st[-1],len(st)) if st else None,(rc or {}).get('digests',{}).get('code_digest')==PRE if rc else None,(r.get('judge') or {}).get('verdict'),r['elapsed_s']))
        if not r['grade']['pass']:
            print('      failed',[k for k,x in r['grade']['checks'].items() if not x]); print('      error',json.dumps(v.get('error'))[:500]); print('      data',json.dumps({k:x for k,x in (v.get('data') or {}).items() if k in('reason','result_kind','provider_used','fixture_results','tool_calls','text','delivered','launched')})[:500])
            print('      calls',[(m['purpose'],m.get('outcome'),m.get('started_at'),m.get('ended_at'),json.dumps(m.get('error'))[:200]) for m in calls(rc)]); print('      setup',[(s[0],s[1],s[2]) for s in r['setup']][:2],'cli',[(l['argv'][0],l['exit'],l['elapsed_s'],l['stderr_tail'][:150]) for l in r['cli_log']][-2:])
            print('      final_text',repr(r.get('final_text'))[:200],'receipt' ,rc is not None, 'outcome',((rc or {}).get('synthetic_evidence') or {}).get('outcome'))
# secrets scan
print('== secrets')
pats={'sk-key':r'sk-[A-Za-z0-9_\-]{16,}','bearer':r'(?i)bearer\s+[A-Za-z0-9._\-]{12,}','oauth':r'(?i)(oauth|refresh_token|access_token|api[_-]?key|authorization|x-api-key|session[_-]?key|password|secret)','email':r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}','jwt':r'eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}','ghp':r'gh[pousr]_[A-Za-z0-9]{20,}','aws':r'AKIA[0-9A-Z]{16}','home':r'/home/[a-z0-9_\-]+','user':r'clebeson','claudecfg':r'\.claude|CLAUDE_CONFIG_DIR|credentials','pem':r'BEGIN [A-Z ]*PRIVATE KEY','google':r'AIza[0-9A-Za-z_\-]{30,}','xox':r'xox[abpr]-[A-Za-z0-9\-]{10,}'}
for D in (E,E2):
    for f in sorted(os.listdir(D)):
        t=open(D+f,encoding='utf-8').read()
        for k,p in pats.items():
            ms=re.findall(p,t)
            if ms:
                c=collections.Counter(m if isinstance(m,str) else m[0] for m in ms)
                print(' ',D[-18:-1],f,k,len(ms),dict(list(c.most_common(6))))
