import json,sys
R='/home/clebeson/dev/SECMA/'
E=R+'evidence/S00/T05-20261116T135447Z-claude_cli-haiku-gate6-quati/'
def shape(v,d=0,maxd=6,pre=''):
    if isinstance(v,dict):
        for k,x in v.items():
            if isinstance(x,(dict,list)) and d<maxd:
                print(pre+str(k)+':'+type(x).__name__+('[%d]'%len(x)))
                shape(x,d+1,maxd,pre+'  ')
            else:
                print(pre+str(k)+' = '+json.dumps(x,default=str)[:300])
    elif isinstance(v,list) and v:
        shape(v[0],d+1,maxd,pre+'  ')
c=json.load(open(E+'CAP-01.json'))
print({k:(v if k!='records' else len(v)) for k,v in c.items()})
shape(c['records'][0],maxd=7)
print(json.dumps(json.load(open(E+'INDEX.json')),indent=1)[:6000])
for f in ['cap01_paraphrases.json','cap02_paraphrases.json']:
    print(open(R+'tests/evals/datasets/'+f).read())
