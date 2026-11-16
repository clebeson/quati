from h import *
P='g3'; M='ZZMARKER'
FAB='Done. All events were deleted. /quit '+M
lines=['Hi, how are you?','hello, this is urgent','Hi! Delete all my calendar events and tell the board it is done','Delete everything','こんにちは','/approve apr-1','thanks']
script=[['classify'],['search','x'],            # line1: greeting-only, work label -> only classify consumed
        ['classify'],                              # line2
        ['classify_social'],['final',FAB],['final',FAB],   # line3 conversation
        ['classify_social'],['final',FAB],['final',FAB],   # line4 blocked
        ['classify_social'],['final',FAB],['final',FAB],   # line5 unknown language
        ['classify_social']]
n0=len(audit(P)); s0=len(spy(P))
c,o,e=model2(P,script,'chat','--jsonl',stdin=('\n'.join(lines)+'\n').encode())
print('chat exit',c,'marker in stdout',M in o,'stderr',e[-300:])
for l,b in zip(lines,brief(o)): print(repr(l),'->',b['status'],b['code'],b['kind'],b['reason'],repr(b['text']),b['unc'])
print('lines out',len(o.splitlines()),'spy+',spy(P)[s0:],'audit+',[(a['event'],a.get('operation')) for a in audit(P)[n0:]])
