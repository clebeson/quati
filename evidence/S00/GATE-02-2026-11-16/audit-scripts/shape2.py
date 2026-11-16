import json
R='<local-path>'
E=R+'evidence/S00/T05-20261116T135447Z-claude_cli-haiku-gate6-quati/'
def shape(v,d=0,maxd=6,pre=''):
    if isinstance(v,dict):
        for k,x in v.items():
            if isinstance(x,(dict,list)) and d<maxd and x:
                print(pre+str(k)+':'+type(x).__name__+('[%d]'%len(x)))
                shape(x,d+1,maxd,pre+'  ')
            else:
                print(pre+str(k)+' = '+json.dumps(x,default=str)[:110])
    elif isinstance(v,list) and v:
        if isinstance(v[0],(dict,list)): shape(v[0],d+1,maxd,pre+'  ')
        else: print(pre+json.dumps(v)[:200])
c=json.load(open(E+'CAP-01.json'))
r=c['records'][0]
r2={k:v for k,v in r.items() if k not in('receipt',)}
shape(r2,maxd=3)
print('---receipt')
rc=r['receipt']; se=rc['synthetic_evidence']
shape({k:v for k,v in rc.items() if k!='synthetic_evidence'},maxd=2)
print('---se keys',list(se))
for i,s in enumerate(se['trajectory']):
    print('STEP',i); shape({k:v for k,v in s.items() if k not in('rank_reasons',)},maxd=2,pre='  ')
print('calls',[(m['index'],m['purpose'],m['model_id'],m['started_at'],m['model_visible'].get('tool_names'),len(m['model_visible']['messages'])) for m in se['model_calls']])
idx=json.load(open(E+'INDEX.json'))
print(json.dumps({k:v for k,v in idx.items() if k!='summary'},indent=1))
for k,v in idx['summary'].items():
    print(k, json.dumps(v)[:1500])
