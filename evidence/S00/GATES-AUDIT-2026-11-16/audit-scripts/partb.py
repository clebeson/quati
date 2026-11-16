import os, sys, json, shutil
from dataclasses import replace
from pathlib import Path
A=Path(__file__).resolve().parent
sys.path.insert(0,'<local-path>'); sys.path.insert(0,str(A))
from h import q, audit
P='pb'
shutil.rmtree(A/P, ignore_errors=True)
assert q(P,'init','--json')[0]==0
q(P,'capabilities','install-fixture','calendar-read','--enable-fixture','--json')
os.environ['QUATI_DATA_DIR']=str(A/P/'data'); os.environ.pop('QUATI_CAPABILITY_CONTEXT',None)
from quati.adapters.local_identity import LocalIdentity
from quati.cli import composition
from quati.application.identity import ScopeAuthorization, context_space_grants
from quati.application.discovery import DiscoveryService
class NoGrants(LocalIdentity):
    def space_grants(self, context): return ()
ident=NoGrants(A/P/'config')
cmds=composition.capability_commands(ident, lambda r: {'sha256':'0'*64,'path':'memory'})
n=len(audit(P))
print('search (no grants):', cmds.search('next appointment calendar')[1]['data'])
code,val=cmds.list(); print('list (no grants): exit',code,val['status'],[c['capability_id']+':'+c['lifecycle'] for c in val['data']['capabilities']])
code,val=cmds.install_fixture('mail-search', enable_fixture=True); print('install+enable (no grants): exit',code,val['status'],val['data'].get('lifecycle'))
code,val=cmds.disable('fixtures.calendar-read@1.0.0'); print('disable (no grants): exit',code,val['status'],val['data'])
print('audit+:',[(e['event'],e.get('operation'),(e.get('decision') or {}).get('verdict')) for e in audit(P)[n:]])
# ask-path registry read outside authorize: AskSession.digests -> registry.catalog
from quati.application import ask as askmod
import inspect
src=inspect.getsource(askmod.AskSession.digests); print('digests reads registry directly:', 'registry.catalog' in src)
# fallback port: any self-asserted context passes
ctx=replace(ident.authenticate(), space_ids=('SPACE-I-MADE-UP',))
d,s=ScopeAuthorization(context_space_grants, composition.system_clock).decide(ctx,'read','space:SPACE-I-MADE-UP'); print('fallback decide with self-asserted space:',d.verdict,d.reason_code,s.readable_space_ids)
# falsy authorization object falls back silently
class Falsy:
    def __bool__(self): return False
    def decide(self,*a): raise AssertionError('never called')
svc=DiscoveryService(cmds.registry, None, None, policy_gate=None, grants=None, clock=composition.system_clock, ids=composition.random_ids, authorization=Falsy())
print('falsy port replaced by fallback:', type(svc.authorization).__name__)
# port raising inside decide -> what happens
class Boom:
    def decide(self,*a): raise RuntimeError('pdp down')
cmds2=composition.capability_commands(LocalIdentity(A/P/'config'), lambda r: {'sha256':'0'*64,'path':'memory'})
cmds2.discovery.authorization=Boom()
try: print('raising port:', cmds2.search('calendar'))
except Exception as ex: print('raising port -> exception propagates:', type(ex).__name__, ex)
# port returning a non-decision / truthy garbage verdict
class Weird:
    def decide(self,ctx,a,r):
        from quati.application.identity import AuthzDecision
        return AuthzDecision('allow','OK',ctx.tenant_id,ctx.actor_id,a,r), None
cmds2.discovery.authorization=Weird(); print('verdict "allow" lowercase:', cmds2.search('calendar')[1]['status'])
