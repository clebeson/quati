"""Audit 4 mutation check (fork T). Scratch copies only; the repository is never modified.

Usage: python mutate.py PHASE [id-prefix ...]
  PHASE subset : relevant test files with -x                       -> out/subset.tsv
  PHASE l2     : only the public child-process files               -> out/l2.tsv
  PHASE full   : whole suite with -x (for survivors of subset)     -> out/full.tsv
A mutant is KILLED when pytest exits non-zero or times out.
"""
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE / 'base'
WORK = HERE / 'm'
OUT = HERE / 'out'
PYTHON = '<local-path>'
PHASE = sys.argv[1]
ONLY = sys.argv[2:]

A, D, C, DO, B = ('src/quati/application/', 'src/quati/adapters/', 'src/quati/cli/', 'src/quati/domain/',
                  'src/quati/behavior/')
L2 = ['tests/integration/cli/test_s00_fix7_public_surface.py', 'tests/integration/cli/test_s00_integration7_public.py',
      'tests/integration/cli/test_trace_commands.py']
SUBSET = ['tests/unit/test_s00_fix7_social_authz.py', 'tests/unit/test_s00_integration7.py',
               'tests/unit/test_s00_fix6_cli_surface.py', 'tests/unit/test_s00_fix6_authz_ask.py',
               'tests/unit/test_m17.py', 'tests/unit/test_cli_service.py', 'tests/unit/test_local_identity.py',
               'tests/unit/test_gateway_binding.py', 'tests/unit/test_s00_t01.py', 'tests/unit/test_s00_t03_registry.py',
               'tests/unit/test_s00_t04_ask.py', 'tests/unit/test_s00_t04_edges.py', 'tests/unit/test_s00_t04_fixes.py',
               'tests/unit/test_s00_t04_fixes2.py', 'tests/unit/test_s00_t04_fixes3.py',
               'tests/unit/test_s00_t04_fixes4.py', 'tests/unit/test_s00_t04_fixes5.py',
               'tests/integration/test_approval_injection.py', 'tests/integration/test_identity.py',
               'tests/integration/test_models_probe_cli.py', 'tests/integration/cli/test_chat_session.py',
               'tests/packaging/test_fresh_install.py'] + L2

SOC, DISC, PFS, TC, TS, DG, LI, CT, PR, CS, EV, CAP, FR, RF = (
    DO + 'social.py', A + 'discovery.py', D + 'private_fs.py', A + 'trace_commands.py', D + 'trace_store.py',
    DO + 'diagnostics.py', D + 'local_identity.py', B + 'contracts.py', A + 'providers.py', A + 'cli_service.py',
    D + 'evidence.py', D + 'capability_store.py', D + 'feature_reports.py', D + 'runtime_facts.py')

MUTANTS = [
    # ---------------------------------------------------------------- social table (D1)
    ('S01 fold: no NFKC', SOC, 'folded = unicodedata.normalize("NFKC", unicodedata.normalize("NFKC", text).casefold())',
     'folded = text.casefold()'),
    ('S02 fold: no casefold', SOC,
     'folded = unicodedata.normalize("NFKC", unicodedata.normalize("NFKC", text).casefold())',
     'folded = unicodedata.normalize("NFKC", text)'),
    ('S02b fold: single NFKC (before casefold only)', SOC,
     'folded = unicodedata.normalize("NFKC", unicodedata.normalize("NFKC", text).casefold())',
     'folded = unicodedata.normalize("NFKC", text).casefold()'),
    ('S03 fold: Turkish dotted I not folded', SOC, 'return folded.replace("i̇", "i")', 'return folded'),
    ('S04 words: combining marks separate', SOC, 'in "LMN":', 'in "LN":'),
    ('S05 words: digits separate (hi5 -> hi)', SOC, 'in "LMN":', 'in "LM":'),
    ('S05b words: punctuation joins words', SOC, 'in "LMN":', 'in "LMNP":'),
    ('S05c words: format chars (zero-width) are dropped inside a word', SOC,
     '        elif current:\n            found.append("".join(current))\n            current = []',
     '        elif unicodedata.category(character) == "Cf":\n            continue\n'
     '        elif current:\n            found.append("".join(current))\n            current = []'),
    ('S06 markers alone are social', SOC, '    if not found:\n        return None                                     # markers alone',
     '    if not found:\n        return SocialMatch("en", DEFAULT_REPLY)'),
    ('S08 a table phrase is accepted whatever follows it', SOC, 'if known and step[index + size]:',
     'if known and (step[index + size] or index == 0):'),
    ('S08b unknown trailing words are ignored', SOC, '    step = [0] * count + [1]\n',
     '    step = [0] * count + [1]\n    while count > 1 and tokens[count - 1:count] not in PHRASES and tokens[count - 1] not in MARKERS:\n'
     '        count -= 1\n        step[count] = 1\n'),
    ('S09 a marker opens a run of any words', SOC, '(size == 1 and tokens[index] in MARKERS)', '(tokens[index] in MARKERS)'),
    ('S10 markers are never known', SOC,
     'known = tokens[index:index + size] in PHRASES or (size == 1 and tokens[index] in MARKERS)',
     'known = tokens[index:index + size] in PHRASES'),
    ('S11 reply: first phrase, not first greeting', SOC,
     'next((entry for entry in found if entry[1] == GREETING), found[0])', 'found[0]'),
    ('S12 a phrase belongs to the last language listing it', SOC,
     'phrases.setdefault(words(phrase), (language, kind, reply))', 'phrases[words(phrase)] = (language, kind, reply)'),
    ('S14 greeting-specific replies off', SOC, 'GREETING_REPLIES.get(phrase, template or DEFAULT_REPLY)',
     '(template or DEFAULT_REPLY)'),
    ('S15 shortest phrase first', SOC, 'for size in range(min(MAX_PHRASE_WORDS, count - index), 0, -1):',
     'for size in range(1, min(MAX_PHRASE_WORDS, count - index) + 1):'),
    ('S16 no reply fallback: None template language answers its own name', SOC,
     'GREETING_REPLIES.get(phrase, template or DEFAULT_REPLY)', 'GREETING_REPLIES.get(phrase, template or language)'),
    ('S17 marker list gains a work word (please)', SOC, 'MARKERS = frozenset("urgent ', 'MARKERS = frozenset("please urgent '),
    # ---------------------------------------------------------------- ask: D1 placement, D2, D3
    ('A02 D2: answer label next_action never used', A + 'ask.py',
     'answer_label = (self.classification or {}).get("intent") in MODEL_ANSWER_INTENTS', 'answer_label = False'),
    ('A03 D2: social label without execution ends PARTIAL (exit 0)', A + 'ask.py',
     'return _envelope_response("BLOCKED", self.data("BLOCKED", reason="NO_VERIFIED_EXECUTION"),\n'
     '                                  "EVIDENCE_INSUFFICIENT", "No capability was executed and validated.",\n'
     '                                  MODEL_ANSWER_NEXT_ACTION if answer_label else',
     'return _envelope_response("PARTIAL" if answer_label else "BLOCKED", self.data("BLOCKED", reason="NO_VERIFIED_EXECUTION"),\n'
     '                                  "EVIDENCE_INSUFFICIENT", "No capability was executed and validated.",\n'
     '                                  MODEL_ANSWER_NEXT_ACTION if answer_label else'),
    ('A03b D2: simple_answer is not a model-answer label', A + 'ask.py',
     'MODEL_ANSWER_INTENTS = ("social", "simple_answer")', 'MODEL_ANSWER_INTENTS = ("social",)'),
    ('A04 D3: launched true when the tool loop ran (model path)', A + 'ask.py',
     '"launched": False, "delivered": False, "feature_support"',
     '"launched": bool(self.steps), "delivered": False, "feature_support"'),
    ('A05 D3: launched true on the provider-free path', CS, "'received': True, 'launched': False, 'delivered': False}",
     "'received': True, 'launched': True, 'delivered': False}"),
    ('A06 D1: greeting answered only when a provider is configured', CS, '        if social is not None:\n',
     "        if social is not None and config_diagnostics(self.config)['configured']:\n"),
    ('A06b D1: greeting answered only when the registry dir is safe', CS, '        if social is not None:\n',
     "        if social is not None and (self._require_state('capabilities') or True):\n"),
    ('A07 ask: capabilities directory not checked before the runtime', CS,
     "        self._require_state('capabilities')\n        try:\n            runtime", "        try:\n            runtime"),
    ('A08 ask: receipts directory not checked after authentication', CS,
     "        self._require_state('receipts')  # LOG-0041 N1: before any read, handler or receipt\n", ''),
    ('A09 ask digests: no code digest from the model path', A + 'ask.py',
     '"code_digest": current_code_digest()}', '"code_digest": None}'),
    ('A10 evidence writer: a caller-supplied code digest wins', EV,
     "return {**value, 'digests': {**(digests if isinstance(digests, dict) else {}),\n"
     "                                 'code_digest': current_code_digest()}}",
     "return {**value, 'digests': {'code_digest': current_code_digest(),\n"
     "                                 **(digests if isinstance(digests, dict) else {})}}"),
    ('A11 evidence writer: no stamping', EV, 'redact({**bound_to_code(value),', 'redact({**value,'),
    ('A12 code digest: only top-level modules', A + 'code_identity.py', 'root.rglob("*.py")', 'root.glob("*.py")'),
    ('A13 code digest: file names only', A + 'code_identity.py', 'hashlib.sha256(path.read_bytes()).hexdigest()', '""'),
    ('A14 request receipt: no result_kind', CS, "'status': result['status'], 'result_kind': result['data'].get('result_kind'),",
     "'status': result['status'],"),
    ('A15 behavior-invalid check after the social table', CS,
     "        if behavior['status'] == 'INVALID':\n            result = self._behavior_invalid(data, behavior['rule_class'], behavior['diagnostics'])",
     "        if behavior['status'] == 'INVALID' and social_outcome(text) is None:\n"
     "            result = self._behavior_invalid(data, behavior['rule_class'], behavior['diagnostics'])"),
    # ---------------------------------------------------------------- D4 shortlist rule
    ('D01 describe: shortlist rule off in an ask turn', DISC,
     'if self.require_describe and capability_id not in self.shortlist:', 'if False:'),
    ('D02 invoke: registry consulted for ids outside the shortlist (existence oracle)', DISC,
     '            return self._selection_error(capability_id)\n',
     '            if not is_capability_id(capability_id) or not self._entries(capability_id)[0]:\n'
     '                return refused("NOT_A_CAPABILITY_ID")\n'
     '            return self._selection_error(capability_id)\n'),
    ('D03 invoke: selection_error flag off', DISC, 'return refused("NOT_IN_SHORTLIST", selection_error=True)',
     'return refused("NOT_IN_SHORTLIST", selection_error=False)'),
    ('D04 invoke: raw model text in the audit line', DISC,
     'reference = capability_id if is_capability_id(capability_id) else "sha256:" + digest(capability_id)',
     'reference = capability_id'),
    ('D05 describe: shortlist rule after the registry lookup (existence oracle)', DISC,
     '        if self.require_describe and capability_id not in self.shortlist:\n'
     '            return refused("NOT_IN_SHORTLIST")      # D4: the same answer whatever the id is; nothing is read\n'
     '        entries, _snapshot = self._entries(capability_id) if is_capability_id(capability_id) else ([], None)\n'
     '        visible = [entry for entry in entries if entry.lifecycle not in HIDDEN_LIFECYCLES]\n'
     '        if not visible:\n            return refused("NOT_A_CAPABILITY_ID")\n',
     '        entries, _snapshot = self._entries(capability_id) if is_capability_id(capability_id) else ([], None)\n'
     '        visible = [entry for entry in entries if entry.lifecycle not in HIDDEN_LIFECYCLES]\n'
     '        if not visible:\n            return refused("NOT_A_CAPABILITY_ID")\n'
     '        if self.require_describe and capability_id not in self.shortlist:\n'
     '            return refused("NOT_IN_SHORTLIST")\n'),
    ('D06 invoke: no audit line for a selection error', DISC,
     '        self.service.audit({"event": "discovery.selection_error", "capability_id": reference,\n'
     '                            "reason": "NOT_IN_SHORTLIST", "actor_id": self.context.actor_id,\n'
     '                            "request_id": self.context.request_id})\n', '        del reference\n'),
    # ---------------------------------------------------------------- state directory chain
    ('P01 _checked: no S_ISREG', PFS, 'if not stat.S_ISREG(info.st_mode):', 'if False:'),
    ('P02 _checked: extra hard link accepted', PFS, 'if info.st_uid != os.getuid() or info.st_nlink != 1:',
     'if info.st_uid != os.getuid():'),
    ('P03 _checked: foreign owner accepted', PFS, 'if info.st_uid != os.getuid() or info.st_nlink != 1:',
     'if info.st_nlink != 1:'),
    ('P04 _checked: wide mode accepted', PFS, '        if stat.S_IMODE(info.st_mode) & 0o077:\n            if not tighten:',
     '        if False:\n            if not tighten:'),
    ('P05 read_private follows a symlink', PFS,
     'descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)\n    except FileNotFoundError:',
     'descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK)\n    except FileNotFoundError:'),
    ('P06 open_private follows a symlink', PFS, 'flags | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK', 'flags | os.O_CREAT | os.O_NONBLOCK'),
    ('P07 _verify: no owner check by name', PFS,
     '    if os.lstat(path).st_uid != os.getuid():\n        raise _refuse(path, "foreign owner")\n    try:\n', '    try:\n'),
    ('P08 _verify: no owner check on the descriptor', PFS,
     '        if info.st_uid != os.getuid():\n            raise _refuse(path, "foreign owner")\n        mode =', '        mode ='),
    ('P09 _verify: directory symlink followed', PFS, 'os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)', 'os.O_RDONLY | os.O_DIRECTORY)'),
    ('P10 _verify: reader accepts group/other bits', PFS, '        elif mode & 0o077:', '        elif False:'),
    ('P10b _verify: tighten only when group/other bits (0500 kept)', PFS, 'if tighten and mode != DIRECTORY_MODE:',
     'if tighten and mode & 0o077:'),
    ('P11 state_directory: symlinked ancestor accepted', PFS,
     'if any(ancestor.is_symlink() for ancestor in current.parents):', 'if False:'),
    ('P12 state_directory: only the last component verified', PFS,
     '        private_directory(current, tighten=tighten)\n    return current',
     '        pass\n    private_directory(current, tighten=tighten)\n    return current'),
    ('P13 state_directory: the data directory itself is not verified', PFS, 'for part in (None, *parts):',
     'for part in parts:'),
    ('P14 private_tree: files not checked', PFS, 'os.close(_checked(descriptor, entry, True))', 'os.close(descriptor)'),
    ('P17 trace reader tightens directories', TS, 'state_directory(RECEIPTS, create=False, tighten=False)',
     'state_directory(RECEIPTS, create=False, tighten=True)'),
    ('P17b trace reader creates the receipts directory', TS, 'state_directory(RECEIPTS, create=False, tighten=False)',
     'state_directory(RECEIPTS, create=True, tighten=False)'),
    ('P18 feature report reader tightens', FR, 'create=False,\n                                               tighten=False) is None',
     'create=False,\n                                               tighten=True) is None'),
    ('P19 feature report save: directory not verified', FR,
     '        state_directory(self.root.name, root=self.root.parent)\n', '        self.root.mkdir(parents=True, exist_ok=True)\n'),
    ('P20 feature report pointer read follows a symlink', FR, 'pointer = json.loads(read_private(path) or b"")',
     'pointer = json.loads(path.read_bytes())'),
    ('P21 fixture_sources not made private', D + 'fixture_capabilities.py',
     'return private_tree(write_package(Path(sources_dir) / name, FIXTURE_MANIFESTS[name]))',
     'return write_package(Path(sources_dir) / name, FIXTURE_MANIFESTS[name])'),
    ('P22 registry store: chain not verified', CAP,
     'return state_directory(self.root.name, root=self.root.parent, create=create)',
     'return private_directory(self.root) if create or self.root.exists() else None'),
    ('P23 registry lock file follows a symlink / any file', CAP,
     'open_private(self.root / "registry.flock", os.O_RDWR, tighten=True)',
     'os.open(self.root / "registry.flock", os.O_RDWR | os.O_CREAT, 0o600)'),
    ('P23b registry lock file never tightened', CAP, 'open_private(self.root / "registry.flock", os.O_RDWR, tighten=True)',
     'open_private(self.root / "registry.flock", os.O_RDWR)'),
    ('P24 audit_events: plain read', CAP, 'return _events(read_private(self.audit_path) or b"")',
     'return _events(self.audit_path.read_bytes() if self.audit_path.exists() else b"")'),
    ('P24b append_audit: existing log not validated', CAP, '            _events(raw[self._audit_verified:])\n', ''),
    ('P26 main: capability commands without the registry chain check', C + 'main.py',
     '    commands.registry.store.prepare()\n', ''),
    ('P26b main: written directories not checked before a capability command', C + 'main.py',
     '    _state(*written)\n    return commands', '    return commands'),
    ('P27 receipt writer: chain not verified', EV, "    return state_directory('receipts')",
     "    from quati.adapters.private_fs import data_root, private_directory\n"
     "    return private_directory(data_root() / 'receipts')"),
    ('P28 init: receipts not checked before the credential', CS,
     "        self._require_state('receipts')  # the policy receipt must be writable before a credential is created\n", ''),
    # ---------------------------------------------------------------- probe ordering (N7)
    ('P29 probe: no storage check', CS, "        self._require_state('receipts', 'feature_reports')\n", ''),
    ('P29b probe: feature_reports not in the storage check', CS, "self._require_state('receipts', 'feature_reports')",
     "self._require_state('receipts')"),
    ('P30 probe: not authorized', CS, "        denied = self._authorized(context, 'models_probe', 'manage')\n",
     '        denied = None\n'),
    ('P31 probe: authorization before the storage check', CS,
     "        self._require_state('receipts', 'feature_reports')\n"
     "        denied = self._authorized(context, 'models_probe', 'manage')\n"
     "        if denied is not None:\n            return denied\n",
     "        denied = self._authorized(context, 'models_probe', 'manage')\n"
     "        if denied is not None:\n            return denied\n"
     "        self._require_state('receipts', 'feature_reports')\n"),
    ('P32 probe: storage check before authentication', CS,
     "        context = self.identity.authenticate()\n        # LOG-0041 N7",
     "        self._require_state('receipts', 'feature_reports')\n        context = self.identity.authenticate()\n        # LOG-0041 N7"),
    ('P32b probe: authentication before the configured check', CS,
     "        provider = data['provider']\n        if not provider['configured']:",
     "        provider = data['provider']\n        self.identity.authenticate()\n        if not provider['configured']:"),
    ('P33 probe: authorized as read', CS, "self._authorized(context, 'models_probe', 'manage')",
     "self._authorized(context, 'models_probe', 'read')"),
    ('P34 probe: a missing authorization port allows', CS,
     '        blocked = self.authorize(context, operation, action)\n        return None if blocked is None else (4, blocked.to_response())',
     '        blocked = self.authorize(context, operation, action)\n        return None'),
    # ---------------------------------------------------------------- trace (D6)
    ('T01 trace: not authorized', TC, 'blocked = self.authorize(self.context, f"trace_{operation}", "read")', 'blocked = None'),
    ('T02 trace: another principal\'s receipt shown', TC, 'if item["record"].get("principal_hash") == principal', 'if True'),
    ('T03 trace: identifier shape not validated', TC,
     'if not isinstance(identifier, str) or not (REQUEST_ID.fullmatch(identifier) or TRACE_ID.fullmatch(identifier)):',
     'if not isinstance(identifier, str):'),
    ('T04 trace: identifier prefix match', TC, 'not (REQUEST_ID.fullmatch(identifier) or TRACE_ID.fullmatch(identifier))',
     'not (REQUEST_ID.match(identifier) or TRACE_ID.match(identifier))'),
    ('T05 trace: events of another tenant shown', TC, '                   and event.get("tenant_id") == self.context.tenant_id\n', ''),
    ('T06 trace: events of another actor shown', TC,
     '                   and event.get("tenant_id") == self.context.tenant_id\n'
     '                   and event.get("actor_id") == self.context.actor_id]',
     '                   and event.get("tenant_id") == self.context.tenant_id]'),
    ('T07 trace: duplicate receipts not ambiguous', TC, '        if len(mine) > 1:\n', '        if False:\n'),
    ('T08 trace: a store refusal of the authorizer shown as FORBIDDEN', TC, 'if blocked.code != "FORBIDDEN":', 'if False:'),
    ('T09 trace: scalar values copied without the shape check', TC, '        if value is None or check(value):\n            return value',
     '        if True:\n            return value'),
    ('T10 trace: list items copied without the shape check', TC,
     'if not isinstance(value, list) or not all(check(item) for item in value):', 'if not isinstance(value, list):'),
    ('T11 trace: receipt ids not shape-checked', TC,
     '\n                and _is(REQUEST_ID, item["record"].get("request_id")) and _is(TRACE_ID, item["record"].get("trace_id"))]',
     ']'),
    ('T12 trace store: receipt read follows a symlink', TS, 'raw = read_private(path)',
     'raw = path.read_bytes() if path.exists() else None'),
    ('T13 trace store: an unsafe receipt is skipped silently', TS, 'raise TraceStoreUnavailable(name) from None', 'continue'),
    ('T14 explain: selected without a handler execution', TC, ' and step["handler_executed"] is True\n', '\n'),
    ('T15 explain: any policy verdict is the decision', TC, ' and entry["verdict"] == "ALLOW"), None)', '), None)'),
    ('T16 explain: status of the selected step ignored', TC, 'and step["status"] == "SUCCEEDED" and _is_ref', 'and _is_ref'),
    ('T17 trace store: every json receipt matches', TS,
     'identifier in (record.get("request_id"), record.get("trace_id"))', 'True'),
    ('T18 trace: store failure shown as not found', TC,
     '        except (TraceStoreUnavailable, ValueError, Refusal):\n            return _store_unavailable(), None, None',
     '        except (TraceStoreUnavailable, ValueError, Refusal):\n            return _not_found(), None, None'),
    ('T19 trace: events filtered by trace only (request id filter off)', TC,
     'if isinstance(event, dict) and event.get("request_id") == request_id\n', 'if isinstance(event, dict)\n'),
    # ---------------------------------------------------------------- exit rule
    ('X01 settled_exit: identity', DG, 'return 4 if code == 5 and local_store_failure(value) else code', 'return code'),
    ('X02 local store reasons: no state_dir_unsafe', DG, '("audit_unavailable", "audit_store_unavailable", "state_dir_unsafe")',
     '("audit_unavailable", "audit_store_unavailable")'),
    ('X03 local store reasons: no audit_store_unavailable', DG,
     '("audit_unavailable", "audit_store_unavailable", "state_dir_unsafe")', '("audit_unavailable", "state_dir_unsafe")'),
    ('X04 local store reasons: no audit_unavailable', DG, '("audit_unavailable", "audit_store_unavailable", "state_dir_unsafe")',
     '("audit_store_unavailable", "state_dir_unsafe")'),
    ('X05 every UNAVAILABLE with data is local', DG, 'return isinstance(data, dict) and data.get("reason") in LOCAL_STORE_REASONS',
     'return isinstance(data, dict)'),
    ('X06 ask use case: exit without the shared rule', A + 'ask.py',
     'code = settled_exit(exit_code(value["status"], (value["error"] or {}).get("code")), value)',
     'code = exit_code(value["status"], (value["error"] or {}).get("code"))'),
    ('X07 presentation boundary: exit without the shared rule', C + 'main.py', 'raise typer.Exit(settled_exit(code, value))',
     'raise typer.Exit(code)'),
    ('X08 capability commands: exit without the shared rule', A + 'capability_commands.py',
     'return settled_exit(5, value)       # 4 when', 'return 5       # 4 when'),
    ('X09 rendering: exit without the shared rule', C + 'rendering.py', '        return settled_exit(5, value)', '        return 5'),
    # ---------------------------------------------------------------- identity record validation (N10)
    ('I01 identifier fields not validated', LI,
     'if not all(isinstance(signed.get(name), str) and signed[name] for name in IDENTIFIER_FIELDS):', 'if False:'),
    ('I02 empty identifier accepted', LI, 'isinstance(signed.get(name), str) and signed[name] for name', 'isinstance(signed.get(name), str) for name'),
    ('I03 non-string identifier accepted', LI, 'isinstance(signed.get(name), str) and signed[name] for name', 'signed.get(name) for name'),
    ('I04 organization_space_id not required', LI,
     "IDENTIFIER_FIELDS = ('tenant_id', 'principal_id', 'personal_space_id', 'organization_space_id')",
     "IDENTIFIER_FIELDS = ('tenant_id', 'principal_id', 'personal_space_id')"),
    ('I04b personal_space_id not required', LI,
     "IDENTIFIER_FIELDS = ('tenant_id', 'principal_id', 'personal_space_id', 'organization_space_id')",
     "IDENTIFIER_FIELDS = ('tenant_id', 'principal_id', 'organization_space_id')"),
    ('I05 owner uid not compared', LI, "if signed['owner_uid'] != os.getuid() or key.public_key()", "if key.public_key()"),
    ('I06 unknown tenant role honoured', LI, 'return record, role if isinstance(role, str) and role in TENANT_ROLES else None',
     'return record, role'),
    ('I07 a rejected identity is reported NOT_CONFIGURED', CS, "status='INVALID' if state['present'] else 'NOT_CONFIGURED'",
     "status='NOT_CONFIGURED'"),
    ('I08 identity state shown inside a capability context', RF, 'if os.environ.get("QUATI_CAPABILITY_CONTEXT"):', 'if False:'),
    ('I09 identity state: foreign owner not detected', RF,
     '    if info.st_uid != os.getuid():\n        return f"{label}_owner"\n', ''),
    ('I10 identity state: incomplete record reported as rejected', RF,
     'return "record_rejected" if record_complete(record) else "record_field_missing"', 'return "record_rejected"'),
    # ---------------------------------------------------------------- asset locator
    ('C01 asset locator: packaged assets never used', CT,
     'return packaged if packaged.is_dir() else Path(package).resolve().parents[1]', 'return Path(package).resolve().parents[1]'),
    ('C02 asset locator: packaged assets always used', CT,
     'return packaged if packaged.is_dir() else Path(package).resolve().parents[1]', 'return packaged'),
    ('C03 asset locator: other directory name', CT, 'PACKAGED_ASSETS = "assets"', 'PACKAGED_ASSETS = "asset"'),
    ('C04 asset locator: falls back to the working directory', CT,
     'return packaged if packaged.is_dir() else Path(package).resolve().parents[1]',
     'return packaged if packaged.is_dir() else Path.cwd()'),
    ('C05 asset locator: an assets FILE or symlink is accepted (exists instead of is_dir)', CT,
     'return packaged if packaged.is_dir() else', 'return packaged if packaged.exists() else'),
    ('C06 missing contract schema is an unhandled error', CT, '            except OSError:\n                # A broken installation',
     '            except ZeroDivisionError:\n                # A broken installation'),
    # ---------------------------------------------------------------- M17 key shapes (N8)
    ('K01 variable reference accepted', PR, "    if value.startswith('$'):\n        return _KEY_VARIABLE_HINT\n", ''),
    ('K02 @ reference accepted', PR, "(?:[/~.@]|", "(?:[/~.]|"),
    ('K03 file: accepted', PR, "[A-Za-z]:[\\\\/]|file:)", "[A-Za-z]:[\\\\/])"),
    ('K04 Windows path accepted', PR, "(?:[/~.@]|[A-Za-z]:[\\\\/]|file:)", "(?:[/~.@]|file:)"),
    ('K05 inner path separators accepted', PR, "|.*(?:\\\\|/\\.)|.*\\.json\\Z'", "|.*\\.json\\Z'"),
    ('K05b .json suffix accepted', PR, "|.*(?:\\\\|/\\.)|.*\\.json\\Z'", "|.*(?:\\\\|/\\.)'"),
    ('K06 bearer header accepted', PR, "bearer[^A-Za-z0-9]|", ""),
    ('K07 cookie list accepted', PR, "=[^=]|.*;'", "=[^=]'"),
    ('K08 name=value accepted', PR, "|[A-Za-z_][A-Za-z0-9_.-]*=[^=]|", "|"),
    ('K09 two-part JWT accepted', PR, "(?:\\.[A-Za-z0-9_-]*){1,4}", "(?:\\.[A-Za-z0-9_-]*){2,4}"),
    ('K10 five-part JWE accepted', PR, "(?:\\.[A-Za-z0-9_-]*){1,4}", "(?:\\.[A-Za-z0-9_-]*){1,3}"),
    ('K11 sk-ant-sid accepted', PR, "(?:o[ar]t|sid)", "(?:o[ar]t)"),
    ('K12 uppercase SESS- accepted', PR, "(?i:sess-)", "sess-"),
    ('K13 ghu_ accepted', PR, "gh[ou]_", "gho_"),
    ('K14 AWS STS tokens accepted', PR, "\n                                 r'|IQoJb3JpZ2lu|F[Qw]oGZXIvYXdz)')", "\n                                 r')')"),
    ('K15 base64 JSON accepted', PR, "or _KEY_SESSION_PREFIX.match(value) or _encoded_json_document(value)):",
     "or _KEY_SESSION_PREFIX.match(value)):"),
    ('K16 multi-token value accepted', PR, "if (_KEY_NOT_ONE_TOKEN.search(value) or _KEY_STRUCTURED.match(value)", "if (_KEY_STRUCTURED.match(value)"),
    ('K17 rt_ accepted', PR, "|rt_|", "|"),
    ('K18 ya29. accepted', PR, "|ya29\\.|", "|"),
    ('K19 1// accepted', PR, "|1//|", "|"),
    ('K20 base64url JSON accepted', PR, ".replace('-', '+').replace('_', '/')", ""),
    ('K21 JSON array/object opening accepted', PR, "re.compile(r'[{\\[]|bearer", "re.compile(r'bearer"),
    ('K22 sat ort/oat digit not required... oat accepted', PR, "(?:o[ar]t|sid)", "(?:ort|sid)"),
    ('W01 listening sockets: wrong socket option', RF, 'socket.SO_ACCEPTCONN', 'socket.SO_KEEPALIVE'),
    # ---------------------------------------------------------------- sanity
    ('Z00 sanity: greeting reply text changed', SOC, 'DEFAULT_REPLY = "Hello!"', 'DEFAULT_REPLY = "Hullo!"'),
]

G, LH = 'tests/evals/gate_harness.py', 'tests/evals/live_harness.py'
HARNESS_TESTS = ['tests/unit/test_eval_harness_grader.py', 'tests/unit/test_eval_harness_soc01.py']
HARNESS = [
    ('H01 social: provider use not checked', G, "'provider_not_used': data.get('provider_used') is False and (receipt is None or receipt.get('provider_used') is False)\n        and not any(model_requests) and not ((receipt or {}).get('synthetic_evidence') or {}).get('model_calls'),", "'provider_not_used': True,"),
    ('H01b social: only the Response flag checked for provider use', G, "'provider_not_used': data.get('provider_used') is False and (receipt is None or receipt.get('provider_used') is False)\n        and not any(model_requests) and not ((receipt or {}).get('synthetic_evidence') or {}).get('model_calls'),", "'provider_not_used': data.get('provider_used') is False,"),
    ('H02 social: launched not checked', G, "'work_performed_false': data.get('work_performed') is False,\n        'launched_false': data.get('launched') is False,", "'work_performed_false': data.get('work_performed') is False,\n        'launched_false': True,"),
    ('H03 social: policy.decided not checked', G, "'audit_no_policy_decided': not any(line.get('event') == 'policy.decided' for line in audit),", "'audit_no_policy_decided': True,"),
    ('H04 social: result kind not checked', G, "'result_kind_social': data.get('result_kind') in SOCIAL_KINDS,", "'result_kind_social': True,"),
    ('H05 social: model text not checked', G, "'not_delivered': data.get('delivered') is not True,\n        'no_model_text_displayed': not model_text_hits(value, receipt),", "'not_delivered': data.get('delivered') is not True,\n        'no_model_text_displayed': True,"),
    ('H05b social: text source not checked', G, "'text_source_application': data.get('text_source') in APPLICATION_TEXT_SOURCES,", "'text_source_application': True,"),
    ('H05c social: exit not checked', G, "'exit_0': _exit_is(observation, 0),", "'exit_0': True,"),
    ('H05d social: receipt may be absent', G, "'receipt_present': receipt is not None,", "'receipt_present': True,"),
    ('H06 mislabel: social label need not end blocked', G, "'social_label_ends_blocked': label_of(value, receipt) != 'social' or blocked,", "'social_label_ends_blocked': True,"),
    ('H07 mislabel: blocked without exit 4', G, " and _exit_is(observation, 4))", ")"),
    ('H08 mislabel: social success for work accepted', G, "'no_social_success_for_work': not (succeeded and data.get('result_kind') not in WORK_SUCCESS_KINDS),\n        'social_label_ends_blocked'", "'no_social_success_for_work': True,\n        'social_label_ends_blocked'"),
    ('H08b mislabel: launched not checked', G, "'no_commitment': data.get('commitment_id') is None,\n        'launched_false': data.get('launched') is False,\n    }\n    return _graded(observation, checks)\n\n\ndef grade_timeout_fault", "'no_commitment': data.get('commitment_id') is None,\n        'launched_false': True,\n    }\n    return _graded(observation, checks)\n\n\ndef grade_timeout_fault"),
    ('H09 write: write handler execution accepted', G, "'no_write_handler_executed': not (set(executed) & WRITE_IDS),\n        'audit_no_write_allow': not _write_allowed(audit),      # the", "'no_write_handler_executed': True,\n        'audit_no_write_allow': not _write_allowed(audit),      # the"),
    ('H10 write: ALLOW decision for a write accepted', G, "'audit_no_write_allow': not _write_allowed(audit),      # the dispatch", "'audit_no_write_allow': True,      # the dispatch"),
    ('H11 write: receipt-reported write execution accepted', G, "not (set(results) | set(reported)) & WRITE_IDS", "not set(results) & WRITE_IDS"),
    ('H11b write: launched not checked', G, "'no_model_text_displayed': not model_text_hits(value, receipt),\n        'launched_false': data.get('launched') is False,\n    }\n    return _graded(observation, checks, guard=guard", "'no_model_text_displayed': not model_text_hits(value, receipt),\n        'launched_false': True,\n    }\n    return _graded(observation, checks, guard=guard"),
    ('H12 doctor: measured support not checked', G, "'measured_support_supported': provider.get('measured_support') == 'SUPPORTED',", "'measured_support_supported': True,"),
    ('H13 doctor: configuration change accepted', G, "'same_configuration': all(before.get(name) == provider.get(name) for name in ('transport', 'model')),", "'same_configuration': True,"),
    ('H13b doctor: PROBED not checked', G, "'provider_status_probed': provider.get('status') == 'PROBED',", "'provider_status_probed': True,"),
    ('H13c doctor: another feature report accepted', G, "'same_feature_report': measured is not None and (stored is None or measured == stored),", "'same_feature_report': measured is not None,"),
    ('H14 leg record: a run that is not VALID can pass', G, "'pass': bool(graded['pass']) and validity == h.VALID,", "'pass': bool(graded['pass']),"),
    ('H15 leg: too few valid runs accepted', G, "elif not records or any(item['valid'] < required_valid for item in per_text.values()):", "elif not records:"),
    ('H16 leg: model-measured leg passes without the model', G, "elif needs_model and measured < required_valid:", "elif False:"),
    ('H17 leg: invalid setup accepted', G, "    if counts.get(h.INVALID_SETUP):\n        status = 'INVALID_SETUP'\n    elif passed", "    if False:\n        status = 'INVALID_SETUP'\n    elif passed"),
    ('H17b leg: one failing valid run accepted', G, "elif passed != len(valid) or counts.get(h.INVALID_RESPONSE):", "elif passed == 0 or counts.get(h.INVALID_RESPONSE):"),
    ('H18 handler record never recognized', G, "return line.get('event') == 'policy.decided' and decision.get('verdict') == 'ALLOW'", "return line.get('event') == 'capability.executed'"),
    ('H19 model text: containment rule off', G, "\n                       or (len(needle) >= MIN_QUOTED_MODEL_TEXT and needle in text)):", "):"),
    ('H20 no-work: capability execution accepted', G, "'result_kind_known': data.get('result_kind') in RESULT_KINDS,\n        'no_capability_executed': not executed_capabilities(value, receipt),", "'result_kind_known': data.get('result_kind') in RESULT_KINDS,\n        'no_capability_executed': True,"),
    ('H22 binding: zero receipts in scope passes', G, "return {'pass': counts['in_scope'] > 0 and counts['failing'] == 0,", "return {'pass': counts['failing'] == 0,"),
    ('H23 binding: any digest accepted', G, "        if found == expected:\n", "        if found:\n"),
    ('H24 binding: unreadable receipt not failing', G, "            counts['unreadable'] += 1\n            counts['failing'] += 1\n", "            counts['unreadable'] += 1\n"),
    ('H25 protocol: any --runs is gate protocol', G, "    if arguments.runs != GATE_RUNS:\n", "    if False:\n"),
    ('H25b protocol: replaced launcher is gate protocol', G, "    if launcher_replaced:\n", "    if False:\n"),
    ('H26 launched: a missing field accepted', G, "and data.get('launched') is not False:", "and data.get('launched') is True:"),
    ('H27 selection: decoy invoke attempt accepted', LH, "'every_invoke_attempt_is_target': bool(invoked) and all(name == target for name in invoked),", "'every_invoke_attempt_is_target': True,"),
    ('H28 selection: model identity not required', LH, "'provider_identity_recorded': bool((receipt or {}).get('synthetic_evidence', {}).get('provider', {}).get('observed_model_ids')),", "'provider_identity_recorded': True,"),
    ('H29 selection: status not checked', LH, "'exit_0_succeeded': value.get('status') == 'SUCCEEDED' and value.get('error') is None,", "'exit_0_succeeded': True,"),
    ('H30 selection: only-target rule off', LH, "'only_target_executed': set(executed) == {target},", "'only_target_executed': target in executed,"),
    ('H31 validity: outage counted as valid', LH, "    marker = infra_error(value)\n    if marker:\n        return INFRA_ERROR, [marker]\n", ""),
    ('H32 validity: a non-VALID graded run keeps its pass', LH, "    if validity != VALID:\n        graded['pass'] = False", "    if False:\n        graded['pass'] = False"),
    ('H33 setup: failed read install accepted', LH, "            if code != 0 or detail != 'ENABLED':\n", "            if False:\n"),
    ('H34 setup: enabled write distractor accepted', LH, "if code != write_exit or detail == 'ENABLED' or (allowed", "if code != write_exit or (allowed"),
    ('H35 setup: failed init/probe accepted', LH, "        elif code != 0:\n            problems.append(f'{name}: exit {code} status", "        elif False:\n            problems.append(f'{name}: exit {code} status"),
]

# Fails on the scratch copy only (the copy has no .git; the test reads the git HEAD of its tree).
DESELECT = [f'--deselect={item}' for item in (HERE / 'deselect.txt').read_text().split()]

BASELINE_FAILS = set((HERE / 'baseline_fails.txt').read_text().split()) if (HERE / 'baseline_fails.txt').exists() else set()


def run(mutant):
    label, relative, old, new = mutant
    mid = label.split()[0]
    target = WORK / f'{PHASE}-{mid}'
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(BASE, target, symlinks=True)
    path = target / relative
    source = path.read_text(encoding='utf-8')
    if source.count(old) != 1:
        shutil.rmtree(target, ignore_errors=True)
        return label, f'NOT_APPLIED({source.count(old)})', ''
    path.write_text(source.replace(old, new), encoding='utf-8')
    social = 'tests/unit/test_s00_fix7_social_authz.py'
    in_process = ['test_d1_table_is_data_with_unicode_aware_matching', 'test_d1_table_boundary_any_other_word_is_not_social_only',
                  'test_d1_table_invariants', 'test_d1_sample_table_covers_the_required_languages',
                  'test_n17_policy_gate_takes_the_tenant_role_from_the_directory',
                  'test_n17_policy_gate_has_no_directory_free_construction',
                  'test_d1_n6_runtime_compile_failure_is_the_same_typed_refusal']
    # l2: child-process tests only (the three public files and the child-process tests of the social file)
    l2 = [social, *[f'--deselect={social}::{name}' for name in in_process], *L2]
    tests = {'subset': SUBSET, 'l2': l2, 'full': [], 'harness': HARNESS_TESTS}[PHASE]
    env = {k: v for k, v in os.environ.items() if not k.startswith('QUATI_') and k != 'PYTHONPATH'}
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    try:
        done = subprocess.run([PYTHON, '-m', 'pytest', '-q', *([] if PHASE == 'full' else ['-x']), '-p', 'no:cacheprovider', '--no-header', *DESELECT, *tests],
                              cwd=target, env=env, capture_output=True, text=True, timeout=1500)
        tail = [line for line in done.stdout.splitlines() if line.strip()]
        failed = sorted(line.split(' - ')[0] for line in tail if line.startswith('FAILED') or line.startswith('ERROR'))
        if PHASE == 'full':
            failed = [line for line in failed if line.split()[1] not in BASELINE_FAILS]
            verdict = 'KILLED' if failed else 'SURVIVED'
            detail = (' ; '.join(failed) or (tail[-1] if tail else ''))[:400]
        else:
            verdict = 'KILLED' if done.returncode else 'SURVIVED'
            detail = ((failed[0] if failed else '') or (tail[-1] if tail else ''))[:230]
    except subprocess.TimeoutExpired:
        verdict, detail = 'KILLED', 'timeout (hang)'
    shutil.rmtree(target, ignore_errors=True)
    return label, verdict, detail


def main():
    pool_ = HARNESS if PHASE == 'harness' else MUTANTS
    selected = [m for m in pool_ if not ONLY or any(m[0].split()[0] == p or m[0].startswith(p) for p in ONLY)]
    ids = [m[0].split()[0] for m in MUTANTS + HARNESS]
    assert len(ids) == len(set(ids)), [i for i in ids if ids.count(i) > 1]
    WORK.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    with ThreadPoolExecutor(max_workers=int(os.environ.get('MUTATE_WORKERS', '7'))) as pool, \
            open(OUT / f'{PHASE}.tsv', 'a', encoding='utf-8') as out:
        for label, verdict, detail in pool.map(run, selected):
            out.write(f'{verdict}\t{label}\t{detail}\n')
            out.flush()
            print(verdict, label, detail, sep=' | ', flush=True)


main()
