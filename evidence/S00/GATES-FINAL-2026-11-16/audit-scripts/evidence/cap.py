import json,collections,sys
EV='<local-path>'
DS='<local-path>'
def run(case,target,ds):
    d=json.load(open(EV+case+'.json'))
    recs=d['records']
    utts=ds['utterances']
    c=collections.Counter(); fails=[]
    keys=collections.Counter(); rids=set(); tids=set()
    cont=0; ranks=collections.Counter(); orders=collections.Counter(); nmc=collections.Counter()
    for r in recs:
        keys[(r['utterance_index'],r['repeat'])]+=1
        resp=r['response']; data=resp['data']; se=r['receipt']['synthetic_evidence']
        traj=se['trajectory']
        ops=[t['operation'] for t in traj]
        ok=True; why=[]
        def chk(n,b):
            nonlocal ok
            c[n]+=b
            if not b: ok=False; why.append(n)
        chk('exit0',r['exit']==0)
        chk('status',resp['status']=='SUCCEEDED' and data['result_status']=='FIXTURE_RESULT' and r['receipt']['status']=='SUCCEEDED')
        chk('seq',ops==['search','describe','invoke'])
        desc=[t for t in traj if t['operation']=='describe']; inv=[t for t in traj if t['operation']=='invoke']
        chk('describe_target',all(t['capability_ref'].split('@')[0]==target for t in desc) and len(desc)==1)
        chk('invoke_target',len(inv)==1 and all(t['capability_ref'].split('@')[0]==target for t in inv))
        he=[t for t in traj if t['handler_executed']]
        chk('one_handler',len(he)==1 and he[0]['operation']=='invoke' and he[0]['capability_ref'].split('@')[0]==target)
        chk('allow',all(t['policy_verdict']=='ALLOW' for t in inv))
        chk('exec_caps',se['outcome']['executed_capabilities']==[target+'@1.0.0'] and r['receipt']['outcome']['executed_capabilities']==[target+'@1.0.0'])
        fr=data['fixture_results']
        chk('verified',len(fr)==1 and fr[0]['outcome_verification']=='VERIFIED' and fr[0]['capability_id']==target)
        if 'expected_arguments' in utts[r['utterance_index']] if isinstance(utts[r['utterance_index']],dict) else False:
            exp=utts[r['utterance_index']]['expected_arguments']
            chk('args_exact',inv[0]['arguments']['input']==exp)
        else: c['args_exact_na']+=1
        mc=se['model_calls']; nmc[len(mc)]+=1
        chk('model_id',len(mc)>0 and all(m['model_id']=='claude-haiku-5-5' for m in mc) and se['provider']['observed_model_ids']==['claude-haiku-5-5'])
        chk('uniq_ids',data['request_id'] not in rids and data['trace_id'] not in tids)
        rids.add(data['request_id']); tids.add(data['trace_id'])
        chk('request_matches',data['request_id']==r['receipt']['request_id']==se.get('request_id',data['request_id']))
        cn=len(se['continuations']); cont+=cn>0
        if cn>0: c['cont_records']+=0; 
        chk('no_invoke_other', all(t['capability_ref'].split('@')[0]==target for t in inv))
        sr=[t for t in traj if t['operation']=='search'][0]
        po=sr.get('presented_order'); chk('po',bool(po) and target in po)
        if po: ranks[po.index(target)+1]+=1; orders[tuple(po)]+=1
        txt=utts[r['utterance_index']]['text'] if isinstance(utts[r['utterance_index']],dict) else utts[r['utterance_index']]
        chk('verdict_deny_free',not any(t['policy_verdict'] not in (None,'ALLOW') for t in traj))
        chk('invoke_count_all',len([t for t in traj if t['operation']=='invoke'])==1)
        chk('cli_status', resp['status']=='SUCCEEDED')
        if ok: c['PASS']+=1
        else: fails.append((r['utterance_index'],r['repeat'],why))
    print(case,'n',len(recs),'keys',len(keys),'maxkey',max(keys.values()),'distinct utt',len({k[0] for k in keys}))
    print(dict(c)); print('fails',fails)
    print('cont records',cont,'ranks',dict(ranks),'distinct orders',len(orders),dict(orders))
    print('model calls per record',dict(nmc))
    return d
ds1=json.load(open(DS+'cap01_paraphrases.json')); ds2=json.load(open(DS+'cap02_paraphrases.json'))
d1=run('CAP-01','fixtures.forecast-lime',ds1)
d2=run('CAP-02','fixtures.calendar-read',ds2)
