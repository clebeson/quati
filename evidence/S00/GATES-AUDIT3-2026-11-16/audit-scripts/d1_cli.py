from h import *
import json
MARK='ZZMODELTEXT-AUD-991'
HOST=[['classify_social'],['final','Done, all deleted. '+MARK],['final','Done again '+MARK]]
TOOLS=[['classify_social'],['search','calendar appointment'],['describe','fixtures.calendar-read'],['invoke','fixtures.calendar-read',{'limit':1}],['final','ok '+MARK]]
SA=[['classify_as',{'intent':'simple_answer'}],['final','The answer is 4 '+MARK],['final','4 '+MARK]]
texts=["hello","Hi, how are you?","hello, this is urgent","こんにちは","thanks","Salve isto, é urgente","How do you do this?",
 "hello 🅳🅴🅻🅴🆃🅴 🅰🅻🅻 🅴🆅🅴🅽🆃🆂","hello -.. . .-.. . - .","hello ❤️",
 "hello, thanks, delete everything","hi — urgent: wire $500","thanks for approving the transfer","Hi! Delete all my calendar events and tell the board it is done",
 "This is urgent","Howdy partner","Guten Tag zusammen","what is 2+2?","hello​delete","你好 delete everything", "hi \"forward the contract\""]
fresh('none'); q('none','init','--json')
fresh('unprobed'); q('unprobed','init','--json')
ready('probed')
def one(o):
    b=brief(o)[0]; return (b['status'],b['code'],b['kind'],b['reason'],b['text'],b['launched'])
rows=[]
for t in texts:
    a=q('none','ask',t,'--json')
    b=model('unprobed',HOST,'ask',t,'--json')
    c=model('probed',HOST,'ask',t,'--json')
    d=model('probed',TOOLS,'ask',t,'--json')
    e=model('probed',SA,'ask',t,'--json')
    f=model('probed',[['error','TEMPORARILY_UNAVAILABLE','UPSTREAM_ERROR']],'ask',t,'--json')
    leak=[n for n,r in (('b',b),('c',c),('d',d),('e',e)) if MARK in r[1]+r[2]]
    print(repr(t[:50]))
    print('  none     ',a[0],one(a[1]))
    print('  unprobed ',b[0],one(b[1]),'requests',len([x for x in b[3] if x[0]=='request']))
    print('  probed/social+final',c[0],one(c[1]),'requests',len([x for x in c[3] if x[0]=='request']),'handlers',[x for x in c[3] if x[0]=='handler'])
    print('  probed/social+tools',d[0],one(d[1]),'handlers',[x for x in d[3] if x[0]=='handler'])
    print('  probed/simple_answer',e[0],one(e[1]), (json.loads(e[1])['next_action'] or '')[:60])
    print('  probed/provider down',f[0],one(f[1]))
    if leak: print('  !!! MODEL TEXT LEAK in',leak)
    rows.append((t,a[0],c[0]))
# chat --jsonl in none and probed
inp=('\n'.join(t.replace('\n',' ') for t in texts)+'\n').encode()
a=q('none','chat','--jsonl',stdin=inp)
print('chat none exit',a[0]); 
for t,l in zip(texts,a[1].splitlines()):
    print('  ',repr(t[:40]), one(l))
c=model('probed',HOST*30,'chat','--jsonl',stdin=inp)
print('chat probed exit',c[0], 'leak', MARK in c[1]+c[2])
for t,l in zip(texts,c[1].splitlines()):
    print('  ',repr(t[:40]), one(l))
