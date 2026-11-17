import sys; sys.path.insert(0,'.')
import h; from h import *
h.RUNNER='<local-path>'
import json
for t in ['Delete all my events','hello, wipe the calendar']:
  r=h.model('x5',[['classify_simple'],['final','MODELTEXTSENTINEL done'],['final','MODELTEXTSENTINEL done']],'ask',t,'--json')
  v=json.loads(r[1].splitlines()[0]); print(t,r[0],v['status'],(v.get('error') or {}).get('code'),(v.get('data') or {}).get('result_kind'),'SENT' in (r[1]+r[2]) or 'MODELTEXT' in r[1]+r[2],[x for x in r[3] if x[0] in('handler','script_left')])
