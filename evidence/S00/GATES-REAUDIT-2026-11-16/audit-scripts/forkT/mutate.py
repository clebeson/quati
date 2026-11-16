"""Mutation harness (scratch copies only). Usage: mutate.py [--full] [id-prefix ...]"""
import os, subprocess, sys, shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import queue

F = Path(__file__).resolve().parent
BASE = F / 'repo'
PY = '<local-path>'
NEW = ['tests/unit/test_s00_fix6_authz_ask.py', 'tests/unit/test_s00_fix6_cli_surface.py',
       'tests/integration/cli/test_behavior_commands.py', 'tests/packaging/test_fresh_install.py',
       'tests/integration/test_identity.py', 'tests/unit/test_m17.py']
A = 'quati/application/'
D = 'quati/adapters/'
M = [
 ('01 ask.run old social rule', A+'ask.py',
  "        if is_greeting_only(self.text):\n",
  "        _v = self.classification\n        if (_v['intent'] == 'social' and _v['work_needed'] is False and _v['next_action'] == 'respond') and is_social_only(self.text):\n"),
 ('02 conversation displays model text', A+'ask.py',
  'data = self.data("CONVERSATION", result_status="RESPONDED", text=template, text_source="application_template",\n                         work_performed=False, actions_taken=[], system_notice=notice,\n                         display_lines=[template, notice])',
  'data = self.data("CONVERSATION", result_status="RESPONDED", text=self.final_text, text_source="application_template",\n                         work_performed=False, actions_taken=[], system_notice=notice,\n                         display_lines=[self.final_text, notice])'),
 ('03 conversation_allowed without greeting requirement', A+'ask.py',
  "return (self.respond_label() and social_reply(self.text, self.greetings) is not None\n",
  "return (self.respond_label() and True\n"),
 ('04a social() no-template shows model-influenced text (classification intent)', A+'ask.py',
  'data = self.data("GREETING", result_status="RESPONDED", text=notice, text_source="application_notice",\n                         work_performed=False, actions_taken=[], system_notice=notice, display_lines=[notice])',
  'data = self.data("GREETING", result_status="RESPONDED", text=str((self.classification or {}).get("intent")), text_source="application_notice",\n                         work_performed=False, actions_taken=[], system_notice=notice, display_lines=[str((self.classification or {}).get("intent")), notice])'),
 ('04b social() no-template makes a second model call', A+'ask.py',
  '        notice = NO_ACTION_NOTICES["en"]\n        data = self.data("GREETING"',
  '        notice = NO_ACTION_NOTICES["en"]\n        try:\n            self.call(ModelRequest((Message("user", self.text),), system="x"), "social_reply")\n        except Exception:\n            pass\n        data = self.data("GREETING"'),
 ('05a list without _denied', A+'capability_commands.py',
  '        denied = self._denied("list", "read")\n        if denied is not None:\n            return denied\n', ''),
 ('05b install_fixture without _denied', A+'capability_commands.py',
  '        denied = self._denied("install_fixture", "manage")\n        if denied is not None:\n            return denied\n', ''),
 ('05c disable without _denied', A+'capability_commands.py',
  '        denied = self._denied("disable", "manage")\n        if denied is not None:\n            return denied\n', ''),
 ('05d install without _denied', A+'capability_commands.py',
  '        denied = self._denied("install", "manage")\n        if denied is not None:\n            return denied\n', ''),
 ('06 catalog_snapshot skips authorize', A+'ask.py',
  'blocked = self.runtime.discovery.authorize(self.context, "ask")', 'blocked = None'),
 ('07a authorize: unlogged ALLOW proceeds', A+'discovery.py',
  'return None if logged else refused("audit_unavailable")', 'return None'),
 ('07b authorize: DENY ignored for manage', A+'discovery.py',
  '        if decision.verdict != "ALLOW":\n            return PortResult("DENIED", "FORBIDDEN", decision.reason_code, {"reason": decision.reason_code},\n                              next_action=SPACE_GRANT_NEXT_ACTION, trace={"handler_executed": False})\n        return None if logged',
  '        if decision.verdict != "ALLOW" and action != "manage":\n            return PortResult("DENIED", "FORBIDDEN", decision.reason_code, {"reason": decision.reason_code},\n                              next_action=SPACE_GRANT_NEXT_ACTION, trace={"handler_executed": False})\n        return None if logged'),
 ('07c authorize: DENY ignored for read', A+'discovery.py',
  '        if decision.verdict != "ALLOW":\n            return PortResult("DENIED", "FORBIDDEN", decision.reason_code, {"reason": decision.reason_code},\n                              next_action=SPACE_GRANT_NEXT_ACTION, trace={"handler_executed": False})\n        return None if logged',
  '        if decision.verdict != "ALLOW" and action != "read":\n            return PortResult("DENIED", "FORBIDDEN", decision.reason_code, {"reason": decision.reason_code},\n                              next_action=SPACE_GRANT_NEXT_ACTION, trace={"handler_executed": False})\n        return None if logged'),
 ('08a decide: manage allowed for any role', A+'identity.py',
  "and self._tenant_role(context) in REGISTRY_MANAGER_ROLES):", "and True):"),
 ('08b decide: owning space from context.space_ids', A+'identity.py',
  "                space_id = self._registry_space(name)\n",
  "                space_id = (context.space_ids or (None,))[-1]\n"),
 ('08c decide: no TENANT_MISMATCH', A+'identity.py',
  "            if name != context.tenant_id:\n", "            if False:\n"),
 ('08d decide: MEMBER may manage', A+'identity.py',
  "REGISTRY_MANAGER_ROLES = ('OWNER', 'ADMIN')", "REGISTRY_MANAGER_ROLES = ('OWNER', 'ADMIN', 'MEMBER')"),
 ('08e decide: space: write allowed', A+'identity.py',
  "reason = 'OK' if action == 'read' else 'ROLE_INSUFFICIENT'", "reason = 'OK'"),
 ('08f decide: registry unknown action allowed', A+'identity.py',
  "elif action == 'read' or (action == 'manage'", "elif action != 'manage' or (action == 'manage'"),
 ('09a GUEST gets organization space', D+'local_identity.py',
  "        if role == 'GUEST':\n            return (record['personal_space_id'],)\n", ""),
 ('09b malformed role treated as OWNER', D+'local_identity.py',
  "return record, role if isinstance(role, str) and role in TENANT_ROLES else None",
  "return record, role if isinstance(role, str) and role in TENANT_ROLES else 'OWNER'"),
 ('09c registry_space ignores tenant', D+'local_identity.py',
  "return record['organization_space_id'] if record['tenant_id'] == tenant_id else None",
  "return record['organization_space_id']"),
 ('09d foreign principal gets role', D+'local_identity.py',
  "        if (context.actor_id, context.tenant_id) != (record['principal_id'], record['tenant_id']):\n            return record, None\n", ""),
 ('10 _probe without authenticate', A+'cli_service.py',
  "        self.identity.authenticate()\n        try:\n            report = self.provider_factory", "        try:\n            report = self.provider_factory"),
 ('11a append_audit without O_NOFOLLOW', D+'capability_store.py',
  "descriptor = open_private(self.audit_path, os.O_WRONLY | os.O_APPEND)",
  "descriptor = os.open(self.audit_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)"),
 ('11b _checked: no nlink check', D+'private_fs.py',
  "if info.st_uid != os.getuid() or info.st_nlink != 1:", "if info.st_uid != os.getuid():"),
 ('11c _checked: no mode check', D+'private_fs.py',
  "if stat.S_IMODE(info.st_mode) & 0o077:", "if False:"),
 ('11d _checked: no S_ISREG check', D+'private_fs.py',
  "if not stat.S_ISREG(info.st_mode):", "if False:"),
 ('11e private_directory: no foreign-owner refusal', D+'private_fs.py',
  '    if info.st_uid != os.getuid():\n        raise _refuse(path, "foreign owner")\n', ''),
 ('11f private_directory: no chmod', D+'private_fs.py',
  "    if stat.S_IMODE(info.st_mode) != DIRECTORY_MODE:\n        os.chmod(path, DIRECTORY_MODE)\n", ""),
 ('11g private_directory: symlink/non-dir accepted', D+'private_fs.py',
  '    if not stat.S_ISDIR(info.st_mode):\n        raise _refuse(path, "symlink or non-directory")\n', ''),
 ('11h open_private without O_NOFOLLOW', D+'private_fs.py',
  "descriptor = os.open(path, flags | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, FILE_MODE)",
  "descriptor = os.open(path, flags | os.O_CREAT | os.O_NONBLOCK, FILE_MODE)"),
 ('11i audit_events reads without private check', D+'capability_store.py',
  "            raw = read_private(self.audit_path)\n",
  "            raw = self.audit_path.read_bytes() if self.audit_path.exists() else None\n"),
 ('11j store _private_root no parent tighten', D+'capability_store.py',
  "            private_directory(parent)\n        private_directory(self.root)", "            pass\n        private_directory(self.root)"),
 ('11k stage_package files with umask', D+'capability_store.py',
  "            write_private(target, entry.data)", "            target.write_bytes(entry.data)"),
 ('11l _checked: no uid check', D+'private_fs.py',
  "if info.st_uid != os.getuid() or info.st_nlink != 1:", "if info.st_nlink != 1:"),
 ('12a key: JWT branch off', A+'providers.py', " or _KEY_SESSION_JWT.fullmatch(value)\n", " or False\n"),
 ('12b key: prefix branch off', A+'providers.py', "or _KEY_SESSION_PREFIX.match(value)):", "or False):"),
 ('12c key: whitespace branch off', A+'providers.py', "if (_KEY_NOT_ONE_TOKEN.search(value) or ", "if (False or "),
 ('12d key: JSON branch off', A+'providers.py', "or value.startswith(('{', '[')) or", "or False or"),
 ('12e key: value leaked into session hint', A+'providers.py',
  "        return _KEY_SESSION_HINT\n", "        return _KEY_SESSION_HINT + ' ' + value\n"),
 ('12f key: value leaked into LIVE_NOT_ALLOWED', A+'providers.py',
  "issues.append(('LIVE_NOT_ALLOWED', 'QUATI_ALLOW_LIVE=1'))",
  "issues.append(('LIVE_NOT_ALLOWED', 'QUATI_ALLOW_LIVE=1 ' + str(self.environ.get(self.config.api_key_env, ''))))"),
 ('12g key: file: branch off', A+'providers.py', " or value[:5].lower() == 'file:':", " or False:"),
 ('12h key: value leaked into path hint', A+'providers.py',
  "        return _KEY_PATH_HINT\n", "        return _KEY_PATH_HINT + ' ' + value\n"),
 ('13a doctor: config_dir not nulled', A+'cli_service.py',
  "        if context() is None:\n            facts['config_dir'] = None\n", ""),
 ('13b doctor: live_calls_allowed constant False', A+'cli_service.py',
  "'live_calls_allowed': bool(self.config.allow_live),", "'live_calls_allowed': False,"),
 ('13c doctor: live_calls_allowed constant True', A+'cli_service.py',
  "'live_calls_allowed': bool(self.config.allow_live),", "'live_calls_allowed': True,"),
 ('13d doctor: measured_support SUPPORTED without report', A+'cli_service.py',
  "        provider['measured_support'] = 'NOT_VERIFIED'\n        if not probe:", "        provider['measured_support'] = 'SUPPORTED'\n        if not probe:"),
 ('13e doctor: behavior diagnostics dropped', A+'behavior_commands.py',
  '        return {**status, "status": "INVALID", "rule_class": exc.rule_class,\n                "diagnostics": [item.to_json() for item in exc.diagnostics]}',
  '        return {**status, "status": "INVALID", "rule_class": exc.rule_class,\n                "diagnostics": []}'),
 ('13f doctor: _measured for unauthenticated', A+'cli_service.py',
  "if self.feature_reports is None or not provider['configured'] or context() is None:",
  "if self.feature_reports is None or not provider['configured']:"),
 ('13g doctor: stale report still measured', A+'cli_service.py',
  "if gate['report_ref'] is None or 'STALE' in (gate['tools'], gate['structured_output']):",
  "if gate['report_ref'] is None:"),
 ('13h doctor: listening_sockets constant 0', D+'runtime_facts.py',
  '"listening_sockets": listening_sockets()}', '"listening_sockets": 0}'),
 ('13i doctor: warnings empty', A+'cli_service.py',
  "                'warnings': _warnings(identity, policy, provider, behavior, facts)}", "                'warnings': []}"),
 ('13j doctor: os_qualification always QUALIFIED', D+'runtime_facts.py',
  '    if system == REFERENCE_OS:\n', '    if True:\n'),
 ('14 ask: ContractViolation propagates', A+'cli_service.py',
  "        except ContractViolation as exc:\n            # CMP-02 on the runtime path", "        except ZeroDivisionError as exc:\n            # CMP-02 on the runtime path"),
 ('15a behavior: no authenticate', A+'behavior_commands.py',
  "        self.identity.authenticate()\n", ""),
 ('15b behavior: absolute outside root accepted', A+'behavior_commands.py',
  '        raise violation(ErrorCode.FORBIDDEN, "PATH_TRAVERSAL", "profile_ref",\n                        "the package is outside the package root", 3) from None',
  '        return package'),
 ('15c behavior: rejected exits 0', A+'behavior_commands.py',
  '        return 2, response("DENIED", {"package": reference, **rejection(exc)}, "CONFIG_INVALID"',
  '        return 0, response("DENIED", {"package": reference, **rejection(exc)}, "CONFIG_INVALID"'),
 ('16a unsupported: trace named S03', A+'cli_service.py', "'worker': 'S02', 'trace': 'S02',", "'worker': 'S02', 'trace': 'S03',"),
 ('16b unsupported: inbox named S03', A+'cli_service.py', "'inbox': 'S02', 'messages': 'S02',", "'inbox': 'S03', 'messages': 'S02',"),
 ('16c config validate FILE treated as no FILE', A+'cli_service.py',
  "        if file is not None:  # profile configuration files belong to ProfilePort (S03)\n            return self.unsupported('config validate FILE')\n", ""),
 ('16d unsupported: behavior named S02', A+'cli_service.py', "'config': 'S03', 'behavior': 'S03'}", "'config': 'S03', 'behavior': 'S02'}"),
 ('16e unsupported: worker named S03', A+'cli_service.py', "'worker': 'S02', 'trace': 'S02',", "'worker': 'S03', 'trace': 'S02',"),
 ('16f main: trace show not registered', 'quati/cli/main.py', "for _name in ('show', 'explain', 'export', 'replay'):", "for _name in ('explain', 'export', 'replay'):"),
 ('16g main: messages alias not registered', 'quati/cli/main.py', "for _name in ('inbox', 'messages'):", "for _name in ('inbox',):"),
 ('16h config validate: INVALID exits 0', A+'cli_service.py',
  "            return 2, response('DENIED', data, 'CONFIG_INVALID', 'The local configuration is present but invalid.',",
  "            return 0, response('DENIED', data, 'CONFIG_INVALID', 'The local configuration is present but invalid.',"),
 ('17a F15 reverted (repeat --enable-fixture SUCCEEDED)', A+'capability_registry.py',
  '                if enable_fixture and existing["lifecycle"] != "ENABLED":', '                if False:'),
 ('17b F15 no-binding enable branch removed', A+'capability_registry.py',
  '            elif enable_fixture:\n', '            elif False:\n'),
 ('18 write_receipt: data dir not made private', D+'evidence.py',
  "    private_directory(directory.parent)  # the data directory itself is owner-only, whatever the umask\n", ""),
 ('19a is_greeting_only: any() dropped (all urgency = greeting)', A+'ask.py',
  "    return (any(word in SOCIAL_VOCABULARY for word in words)\n            and all(", "    return (bool(words)\n            and all("),
 ('19b greeting-only: MODEL_LABEL_NOT_SOCIAL note dropped', A+'ask.py',
  'notes = [] if self.respond_label() else ["MODEL_LABEL_NOT_SOCIAL"]', 'notes = []'),
 ('19c conversation: NO_SEARCH_ON_WORK continuation not required', A+'ask.py',
  '                and any(item["reason"] == "NO_SEARCH_ON_WORK" for item in self.continuations))', '                and True)'),
 ('19d conversation: empty reply accepted', A+'ask.py',
  '        if not (self.final_text or "").strip():\n            return _envelope_response("BLOCKED", self.data("BLOCKED", reason="EMPTY_SOCIAL_REPLY")', '        if False:\n            return _envelope_response("BLOCKED", self.data("BLOCKED", reason="EMPTY_SOCIAL_REPLY")'),
 ('19e catalog_access omitted from receipt', A+'ask.py',
  '        if refusal is not None:\n            receipt["catalog_access"] = refusal\n', ''),
 ('19f rendering: Refusal not typed', 'quati/cli/rendering.py', "    if isinstance(exc, Refusal):", "    if False:"),
 ('19g DiscoveryService accepts missing port', A+'discovery.py',
  '        if authorization is None:\n            raise TypeError("DiscoveryService requires an AuthorizationPort")\n', ''),
 ('19h authz.decided record not written', A+'discovery.py',
  '            self.audit({"event": "authz.decided", "operation": operation,', '            (lambda e: None)({"event": "authz.decided", "operation": operation,'),
]

def setup_workers(n):
    ws = []
    for i in range(n):
        w = F / f'w{i}'
        if not w.exists():
            subprocess.run(['cp', '-al', str(BASE), str(w)], check=True)
            shutil.rmtree(w / 'src')
            shutil.copytree(BASE / 'src', w / 'src')
        ws.append(w)
    return ws

def run(w, mut, full):
    name, rel, old, new = mut
    path = w / 'src' / rel
    orig = (BASE / 'src' / rel).read_text()
    if orig.count(old) != 1:
        return f'{name}\n   -> NOT_APPLIED (count={orig.count(old)})'
    path.write_text(orig.replace(old, new))
    try:
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        for k in ('QUATI_ALLOW_LIVE', 'QUATI_LIVE_EVAL', 'PYTHONPATH'):
            env.pop(k, None)
        c = subprocess.run([PY, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '--no-header', f'--rootdir={w}',
                            *([] if full else NEW)], cwd=str(w), env=env, capture_output=True, text=True, timeout=1500)
        lines = [l for l in c.stdout.splitlines() if l.strip()]
        tail = lines[-1] if lines else c.stderr[-300:]
        fails = [l[7:150] for l in lines if l.startswith(('FAILED', 'ERROR'))]
        real = [f for f in fails if 'code_digest' not in f]
        verdict = 'KILLED' if real else ('SURVIVED' if c.returncode == 0 or fails else 'KILLED?')
        return f'{name}\n   -> {verdict} | {tail} | n={len(fails)} | {real[:4]}'
    finally:
        path.write_text(orig)

if __name__ == '__main__':
    args = sys.argv[1:]
    full = '--full' in args
    only = [a for a in args if a != '--full']
    todo = [m for m in M if not only or any(m[0].startswith(o) for o in only)]
    ws = setup_workers(6)
    q = queue.Queue()
    for w in ws:
        q.put(w)
    def job(m):
        w = q.get()
        try:
            return run(w, m, full)
        except Exception as e:
            return f'{m[0]}\n   -> HARNESS_ERROR {e!r}'
        finally:
            q.put(w)
    with ThreadPoolExecutor(6) as ex:
        for r in ex.map(job, todo):
            print(r, flush=True)
