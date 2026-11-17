import sys; sys.path.insert(0,'.')
from h import *
import json
CLAIM='MODELTEXTSENTINEL Done, everything deleted and the board notified.'
ready('x5', fixtures=('calendar-read','mail-search'))
def run(name, script, text, *extra, stdin=None, argv=None):
    a=argv or ('ask',text,'--json')
    r=model('x5',script,*a,stdin=stdin)
    leaked = CLAIM.split()[0] in (r[1]+r[2])
    try:
        v=json.loads(r[1].splitlines()[0]); d=v.get('data') or {}
        s=(v['status'],(v.get('error') or {}).get('code'),d.get('result_kind'),d.get('reason'),d.get('work_performed'))
    except Exception: s=('??',r[1][:100],r[2][-150:])
    sp=[x for x in r[3] if x[0] in ('handler','script_left')]
    print(f'{name:38} exit={r[0]} {s} spy={sp} SENTINEL_IN_OUTPUT={leaked}',flush=True)
run('NONE_FITS after search',[['classify'],['search','next appointment calendar'],['invoke','NONE_FITS',{}],['final',CLAIM]],'Find my next appointment')
run('NONE_FITS without search',[['classify'],['invoke','NONE_FITS',{}],['final',CLAIM]],'Find my next appointment')
run('empty search outcome then final',[['classify'],['search','zzzqq xxyyww'],['final',CLAIM],['final',CLAIM]],'Do something exotic')
run('empty search then NONE_FITS',[['classify'],['search','zzzqq xxyyww'],['invoke','NONE_FITS',{}],['final',CLAIM]],'Do something exotic')
run('invoke unlisted id',[['classify'],['search','zzzqq xxyyww'],['invoke','fixtures.calendar-read',{'limit':1}],['final',CLAIM]],'Do something exotic')
run('final only (no tools) x2',[['classify'],['final',CLAIM],['final',CLAIM]],'Delete all my events')
run('final only x3',[['classify'],['final',CLAIM],['final',CLAIM],['final',CLAIM]],'Delete all my events')
run('social label on non-table text',[['classify_social'],['final',CLAIM],['final',CLAIM]],'Delete all my events')
run('social label, text hello please',[['classify_social'],['final',CLAIM],['final',CLAIM]],'hello, wipe the calendar')
run('simple_answer label',[['classify_as',{'intent':'simple_answer','work_needed':False,'reason_code':'SIMPLE'}],['final',CLAIM],['final',CLAIM]],'Delete all my events')
run('read handled normally',[['classify'],['search','next appointment calendar'],['describe','fixtures.calendar-read'],['invoke','fixtures.calendar-read',{'limit':1}],['final',CLAIM]],'Find my next appointment')
run('read but invalid input',[['classify'],['search','next appointment calendar'],['describe','fixtures.calendar-read'],['invoke','fixtures.calendar-read',{'limit':'abc'}],['final',CLAIM],['final',CLAIM]],'Find my next appointment')
run('write fixture (not installed)',[['classify'],['search','create calendar event'],['invoke','fixtures.calendar-write',{'title':'x','start':'2026-11-20T10:00:00Z','end':'2026-11-20T11:00:00Z'}],['final',CLAIM],['final',CLAIM]],'Create an event')
run('chat none-fits',[['classify'],['search','zzzqq'],['invoke','NONE_FITS',{}],['final',CLAIM]],'', argv=('chat','--jsonl'),stdin=b'Do something exotic\n')
