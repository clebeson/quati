import json,glob,collections,re
EV='<local-path>'
CD='f9029dea81304be64ac528008e1e5021d628d1b32e9081bb329689daf5395db8'; AD='cbaea523699d41aeba47987db0346e41b1a969fb5d48b68c71ab96ec21aee0a2'
kinds=collections.Counter(); both=collections.Counter(); bad=[]
ts=[]
def walk(o,path,f):
    if isinstance(o,dict):
        if 'kind' in o and isinstance(o['kind'],str) and o['kind'].endswith('receipt') or ('digests' in o and 'evidence_version' in o):
            k=o.get('kind'); kinds[(f,k)]+=1
            dg=o.get('digests',{})
            if dg.get('code_digest')==CD and dg.get('asset_digest')==AD: both[(f,k)]+=1
            else: bad.append((f,path,k,dg.get('code_digest'),dg.get('asset_digest')))
        for k,v in o.items():
            if k in('started_at','ended_at','measured_at') and isinstance(v,str): ts.append((v,f,path))
            walk(v,path+'/'+k,f)
    elif isinstance(o,list):
        for i,v in enumerate(o): walk(v,path+'/%d'%i,f)
for f in sorted(glob.glob(EV+'*.json')):
    n=f.split('/')[-1]
    if n in('INDEX.json',): continue
    walk(json.load(open(f)),'',n)
print(sum(kinds.values()),sum(both.values()),len(bad)); print(kinds); print(bad[:5])
ts.sort(); print(ts[0],ts[-1])
p=json.load(open(EV+'PREREG.json'))
s=json.dumps(p); print(re.findall(r'20\d\d-\d\d-\d\dT[\d:.+Z-]+',s)[:10], p['run_id'])
