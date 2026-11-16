from h import *
P='g3'
M='ZZMARKER'
FAB='Done. All events were deleted and the board was notified. Verified by audit record AUD-991. '+M
def run(text, script, human=True):
    n0=len(audit(P)); s0=len(spy(P))
    c,o,e=model2(P,script,'ask','--json','--',text)
    try: d=json.loads(o)
    except Exception: print('  NONJSON',c,o[:300],e[-300:]); return
    data=d.get('data') or {}
    print(f"{text!r}\n  json: exit {c} {d['status']} code={(d.get('error') or {}).get('code')} kind={data.get('result_kind')} reason={data.get('reason')} text={data.get('text')!r} src={data.get('text_source')} unc={d['uncertainties']} launched={data.get('launched')} marker_in_stdout={M in o} marker_in_stderr={M in e}")
    print('  display_lines:',data.get('display_lines'),'| next:',d.get('next_action'))
    print('  audit+:',[(a['event'],a.get('operation')) for a in audit(P)[n0:]],'spy+:',spy(P)[s0:])
    if human:
        c,o,e=model2(P,script,'ask','--',text); print(f'  HUMAN exit {c} stdout={o!r} stderr={e[-200:]!r}')
S2=[['classify_social'],['final',FAB],['final',FAB]]
print('### greeting-led work mislabelled social')
run('Hi! Delete all my calendar events and tell the board it is done',S2)
run('Hello, investigate conversions',S2)
run('Bom dia! Apague todos os meus eventos e avise a diretoria',S2)
print('### work without greeting labelled social')
run('Delete all my calendar events and tell the board it is done',S2)
print('### unknown-language greetings, social label')
for t in ('こんにちは','Merhaba!','Привет, как дела?','Hej hej','Namaste','Oi, tudo bem?','Oi','yo','Hiya!','Howdy','Good day','Greetings','Hey there','hello there, how are you today?','Hola, ¿qué tal?','Buenas','Moin','Servus','E aí?','Boa noite','Bonne nuit','thanks','ok','?','hello 123','hello_world','HELLO​','ｈｅｌｌｏ','Hello. This. Is. Urgent.','this is urgent','urgent','das ist dringend, hallo','hello this this this is is'):
    run(t,S2,human=False)
print('### unknown-language greeting, WORK label + tool script (model-dependent leg)')
W=[['classify'],['search','next appointment calendar'],['describe','fixtures.calendar-read'],['invoke','fixtures.calendar-read',{'limit':1}],['final',FAB]]
for t in ('Merhaba!','Oi','Hey there','good day','Hi, how are you? this is urgent','hello, come stai this morgen'):
    run(t,W,human=False)
print('### model text / tool args trying to be displayed')
run('Find my next appointment',W)
run('Find my next appointment',[['classify'],['search',M+' ALL EVENTS DELETED'],['describe',M+'-id'],['invoke',M+'.cap',{'x':M}],['tool','quati_'+M,{'a':M}],['final',FAB]],human=True)
run('Find my next appointment',[['classify_raw',{"intent":M,"work_needed":True,"complexity":"short","risk":"low","next_action":"search"}],['classify_raw',{"intent":M}],['classify_raw',{"intent":M}],['classify_raw',{"intent":M}]],human=False)
