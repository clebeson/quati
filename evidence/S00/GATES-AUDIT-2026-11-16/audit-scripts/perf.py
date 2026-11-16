import os, sys, time, shutil, threading, json
from pathlib import Path
A=Path(__file__).resolve().parent
sys.path.insert(0,'<local-path>'); sys.path.insert(0,str(A))
from h import q
P='perf'; shutil.rmtree(A/P, ignore_errors=True); q(P,'init','--json'); q(P,'capabilities','install-fixture','calendar-read','--enable-fixture','--json')
os.environ['QUATI_DATA_DIR']=str(A/P/'data')
from quati.adapters.local_identity import LocalIdentity
from quati.cli import composition
ident=LocalIdentity(A/P/'config'); cmds=composition.capability_commands(ident, lambda r: {'sha256':'0'*64,'path':'m'})
turn=cmds.discovery.begin_turn(cmds.context)
t=time.perf_counter(); n=300
for i in range(n): turn.authorize('search')
dt=(time.perf_counter()-t)/n; print(f'authorize(): {dt*1000:.2f} ms per call (identity reload + Ed25519 verify + fsynced append)')
t=time.perf_counter()
for i in range(n): ident.space_grants(cmds.context)
print(f'  of which space_grants (reads identity.json AND device.key, verifies): {(time.perf_counter()-t)/n*1000:.2f} ms')
size=(A/P/'data/capabilities/audit.jsonl').stat().st_size; print('audit bytes per authz record ~', size//(n+8))
# concurrent appends from 8 threads x 200: any torn/interleaved lines?
def w():
    tn=cmds.discovery.begin_turn(cmds.context)
    for i in range(200): tn.authorize('search')
ts=[threading.Thread(target=w) for _ in range(8)]; [x.start() for x in ts]; [x.join() for x in ts]
bad=0; lines=(A/P/'data/capabilities/audit.jsonl').read_bytes().splitlines()
for l in lines:
    try: json.loads(l)
    except Exception: bad+=1
print('lines',len(lines),'unparseable',bad)
