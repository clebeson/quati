import json,re
G='<local-path>'
i=json.load(open(G+'INDEX.json'))
print([k for k in i]); 
for k in i:
    if re.search('cost|usage|provider_calls|gates|verdict',k): print(k,json.dumps(i[k])[:700])
for c in ('CAP-03','CAP-05'):
    d=json.load(open(G+c+'.json')); print(c,{k:(v if len(json.dumps(v))<200 else '..') for k,v in d.items()})
b=json.load(open(G+'BEH.json')); print({k:(v if len(json.dumps(v))<250 else '..') for k,v in b.items()})
