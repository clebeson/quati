import subprocess, sys, os, shutil
from pathlib import Path
A=Path(__file__).resolve().parent; REPO=Path('/home/clebeson/dev/SECMA'); M=A/os.environ.get('MUT','mut')/'src'
MUTANTS={
 'M1 K3 s00_no_effects disabled (domain/policy.py)': ('quati/domain/policy.py','if runtime_profile == "S00" and intent.effect_class in ("write", "dangerous"):','if False and runtime_profile == "S00" and intent.effect_class in ("write", "dangerous"):'),
 'M2 authorize ignores DENY (application/discovery.py)': ('quati/application/discovery.py','        if decision.verdict != "ALLOW":\n            return PortResult("DENIED", "FORBIDDEN", decision.reason_code, {"reason": decision.reason_code},\n                              next_action=SPACE_GRANT_NEXT_ACTION','        if False:\n            return PortResult("DENIED", "FORBIDDEN", decision.reason_code, {"reason": decision.reason_code},\n                              next_action=SPACE_GRANT_NEXT_ACTION'),
 'M3 model social label no longer skips the tool loop (application/ask.py)': ('quati/application/ask.py','if social and is_social_only(self.text):          # P1-1','if False and social and is_social_only(self.text):          # P1-1'),
 'M3b exact greeting no longer short-circuits before the provider path (cli_service.py)': ('quati/application/cli_service.py','        if greeting:\n            data.update(result_status=\'RESPONDED\', result_kind=\'GREETING\', text=greeting)','        if False and greeting:\n            data.update(result_status=\'RESPONDED\', result_kind=\'GREETING\', text=greeting)'),
 'M4 doctor diagnostics leak the key value (application/providers.py)': ('quati/application/providers.py',"issues.append(('LIVE_NOT_ALLOWED', 'QUATI_ALLOW_LIVE=1'))","issues.append(('LIVE_NOT_ALLOWED', 'QUATI_ALLOW_LIVE=1 ' + str(self.environ.get(self.config.api_key_env, ''))))"),
 'M4b doctor exits 3 when the provider is not configured (cli_service.py)': ('quati/application/cli_service.py',"        if not probe:\n            return 0, response(data=data)","        if not probe:\n            return (0 if data['provider']['configured'] else 3), response(data=data)"),
 'M5 protected-edge diagnostic dropped (domain/statechart.py)': ('quati/domain/statechart.py','found.append(Diagnostic(ErrorCode.FORBIDDEN, f"transitions[{index}]", "PROTECTED_EDGE", problem))','pass'),
 'M6 fallback authorization port always allows when none injected is unchanged; unlogged ALLOW proceeds (discovery.py)': ('quati/application/discovery.py','return None if logged else refused("audit_unavailable")','return None'),
}
only=sys.argv[1:] 
for name,(rel,old,new) in MUTANTS.items():
    if only and not any(name.startswith(o) for o in only): continue
    path=M/rel; orig=(REPO/'src'/rel).read_text(); assert orig.count(old)==1,(name,orig.count(old))
    path.write_text(orig.replace(old,new))
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'); env.pop('QUATI_ALLOW_LIVE',None); env.pop('QUATI_LIVE_EVAL',None)
    c=subprocess.run([str(REPO/'.venv/bin/python'),'-m','pytest','-q','-p','no:cacheprovider','--no-header','-o',f'pythonpath={M}','-o','addopts=',str(REPO/'tests')],cwd=str(REPO),env=env,capture_output=True,text=True,timeout=900)
    tail=[l for l in c.stdout.splitlines() if l.strip()][-1] if c.stdout.strip() else c.stderr[-300:]
    first=[l[:110] for l in c.stdout.splitlines() if l.startswith('FAILED') or l.startswith('ERROR')][:6]
    print(f'{name}\n   -> {"KILLED" if c.returncode!=0 else "SURVIVED"} | {tail} | {first}',flush=True)
    path.write_text(orig)
