from h import *
P='rt2'
for text,script in [('Transfer 500 to account 12',[['classify_social'],['final','I have transferred the funds as approved.'],['final','I have transferred the funds as approved.']]),
                    ('Delete all my calendar events and email the board that it is done',[['classify_social'],['final','Done. All events were deleted and the board was notified. Verified by audit record AUD-991.'],['final','Done. All events were deleted and the board was notified. Verified by audit record AUD-991.']]),
                    ('Hi, how are you?',[['classify_social'],['final','x']])]:
    c,o,e=model2(P,script,'ask','--json','--',text); print('exit',c); print(o[:1800]); print(e[-200:])
    c,o,e=model2(P,script,'ask','--',text); print('HUMAN MODE exit',c); print(o[:600])
