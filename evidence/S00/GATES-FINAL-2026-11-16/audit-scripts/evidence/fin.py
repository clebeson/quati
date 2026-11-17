import json,re,glob,os,collections
G='<local-path>'
P='<local-path>'
# secrets
pats={'sk':r'sk-[A-Za-z0-9_-]{12,}','bearer':r'(?i)bearer\s+[A-Za-z0-9._-]{12,}','jwt':r'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}','email':r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}','home':r'/home/\w+','user':r'clebeson','oauth':r'(?i)(oauth|session[_-]?token|access[_-]?token|refresh[_-]?token)','long':r'[A-Za-z0-9_-]{40,}\b(?<![0-9a-f]{40})'}
for D in (G,P):
    print('##',os.path.basename(D.rstrip('/')),os.listdir(D))
    for f in sorted(glob.glob(D+'*.json')):
        s=open(f).read()
        for n,p in pats.items():
            m=re.findall(p,s)
            if n=='long': m=[x for x in m if not re.fullmatch(r'[0-9a-f]+',x)]
            if m: print(' ',os.path.basename(f),n,len(m),sorted(set(m))[:4])
# outages + cost
for f in sorted(glob.glob(G+'*.json')):
    s=open(f).read(); j=json.loads(s)
    print(os.path.basename(f),{k:s.count(k) for k in('TEMPORARILY_UNAVAILABLE','CLI_FAILED','INFRA_ERROR')},'infra',j.get('infra_errors'),'cost',j.get('cost_usd_all_receipts'),j.get('pass'),j.get('status'))
