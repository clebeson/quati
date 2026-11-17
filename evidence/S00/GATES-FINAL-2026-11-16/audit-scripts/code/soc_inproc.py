import sys; sys.path.insert(0,'<local-path>'); sys.path.insert(0,'.')
from quati.domain.social import social_match
from texts import *
bad=[];miss=[]
def run(label,items):
    for t,e in items:
        m=social_match(t)
        tag='GREETING' if m else 'MODEL'
        flag=''
        if e=='N' and m: flag='  <== P1 request-bearing answered as greeting'; bad.append(t)
        if e=='S' and not m: flag='  <== P3 social not answered'; miss.append(t)
        print(f'{label} {tag:8} {t!r}{flag}')
run('audit',AUDIT)
run('mine-N',[(t,'N') for t in REQ])
run('mine-S',[(t,'S') for t in SOC])
print('P1 count',len(bad),bad); print('P3 count',len(miss),miss)
print('REQ n',len(REQ),'SOC n',len(SOC))
