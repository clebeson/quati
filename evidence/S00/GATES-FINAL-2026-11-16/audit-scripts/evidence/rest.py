import json,re,collections,glob,os
EV='<local-path>'
d=json.load(open(EV+'SOC-01.json'))
for leg in ['c_outside_table_greeting','d_greeting_led_work','h_model_dependent_urgent']:
    L=d['legs'][leg]; print(leg,L['label_distribution'],L['status'],L['valid_n'],L['required_valid_per_text'],L['per_text'] if leg[0]=='h' else '')
print('CHAT',json.dumps(d['chat'])[:2500])
w=json.load(open(EV+'WRITE-01.json'))
print([k for k in w])
recs=w['records']; print(len(recs))
c=collections.Counter()
for r in recs:
    resp=r['response'];dd=resp['data']
    aud=r.get('audit',[])
    allow_write=[a for a in aud if a.get('decision',{}).get('verdict')=='ALLOW' and 'publish' in json.dumps(a.get('decision',{}))+json.dumps(a.get('resource_ref',''))]
    inv=[a for a in aud if a.get('event')=='policy.decided']
    c[(r['text'][:40],r['exit'],resp['status'],json.dumps(r.get('executed')),len(allow_write),len(inv))]+=1
for k,v in c.items(): print(v,k)
print(json.dumps(recs[0]['response'])[:1800])
print([a.get('event') for a in recs[0]['audit']])
for k in w:
    if k!='records': print(k,json.dumps(w[k])[:400])
