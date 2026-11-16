"""Mutation check of integration step 8 (LOG-0045): every mutant the third audit, part 3, reported as
surviving (evidence/S00/GATES-AUDIT3-2026-11-16/audit-scripts/forkT: full.tsv, l2.tsv, harness.tsv),
re-derived on the current code, plus the mutants of this step's own changes.

Scratch copies only; the repository is never modified.

Usage: python mutation_check_script.py REPOSITORY SCRATCH_DIR [id ...]

Each mutant is applied to its own copy of ``src``, ``tests``, ``examples``, ``contracts``,
``pyproject.toml`` and the slice file the harness reads, and its selection is run from that copy (the
in-process tests import the copy through the pytest ``pythonpath``; the child processes of the public
tests import it because the tests derive the source path from their own location). A mutant is KILLED
when pytest fails; the first failing test is recorded. ``tier`` L2 means the selection holds only
child-process tests of the public entry; L1 means in-process tests; H means the harness grader tests.
"""
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPOSITORY, SCRATCH = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
ONLY = sys.argv[3:]
PYTHON = REPOSITORY / '.venv' / 'bin' / 'python'
A, D, C, DO, B = ('src/quati/application/', 'src/quati/adapters/', 'src/quati/cli/', 'src/quati/domain/',
                  'src/quati/behavior/')
SOC, PFS, TC, TS, DG, LI, CT, CS, CAP, FR, RF = (
    DO + 'social.py', D + 'private_fs.py', A + 'trace_commands.py', D + 'trace_store.py', DO + 'diagnostics.py',
    D + 'local_identity.py', B + 'contracts.py', A + 'cli_service.py', D + 'capability_store.py',
    D + 'feature_reports.py', D + 'runtime_facts.py')
G, LH = 'tests/evals/gate_harness.py', 'tests/evals/live_harness.py'
PUB = 'tests/integration/cli/test_s00_integration8_public.py'
UNIT = 'tests/unit/test_s00_integration8.py'
MATRIX = 'tests/integration/cli/test_s00_fix8_store_matrix.py'
TRACE = 'tests/integration/cli/test_trace_commands.py'
SOCIAL_L1 = ['tests/unit/test_s00_fix8_social_outcomes.py', UNIT, 'tests/unit/test_s00_fix7_social_authz.py', '-k',
             'x4 or table or s05c or s17 or test_e_ and not removed_language and not sample_is and not request_bearing']
HARNESS = ['tests/unit/test_eval_harness_grader.py', 'tests/unit/test_eval_harness_soc01.py']


def pub(expression):
    return [PUB, '-k', expression]


def unit(expression):
    return [UNIT, '-k', expression]


FOLD = 'folded = unicodedata.normalize("NFKC", unicodedata.normalize("NFKC", text).casefold())'
LOCK = 'os.fdopen(open_private(self.root / "registry.flock", os.O_RDWR), "a+b")'
REASONS = ('LOCAL_STORE_REASONS = ("audit_unavailable", "audit_store_unavailable", "state_dir_unsafe",\n'
           '                       "feature_report_not_stored")')
# (id and description, origin table, tier, file, old, new, pytest selection)
MUTANTS = [
    # ------------------------------------------------------------------ survivors of the full suite (full.tsv)
    ('W01 listening sockets: SO_ACCEPTCONN -> SO_KEEPALIVE', 'full', 'L2', RF, 'socket.SO_ACCEPTCONN', 'socket.SO_KEEPALIVE',
     pub('t1')),
    ('P23 registry lock file opened with plain os.open', 'full', 'L1', CAP, LOCK,
     'os.fdopen(os.open(self.root / "registry.flock", os.O_RDWR | os.O_CREAT, 0o600), "a+b")', unit('p23')),
    ('P23b registry lock file: a wider mode is repaired instead of refused', 'full', 'L1', CAP, LOCK,
     'os.fdopen(__import__("quati.adapters.private_fs", fromlist=["_checked"])._checked(os.open(self.root / '
     '"registry.flock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600), self.root / '
     '"registry.flock", True), "a+b")', unit('p23')),
    ('P06 private open follows a symlink (O_NOFOLLOW dropped)', 'full', 'L1', PFS,
     'return os.open(path, flags | os.O_NOFOLLOW | os.O_NONBLOCK, FILE_MODE)',
     'return os.open(path, flags | os.O_NONBLOCK, FILE_MODE)', unit('p23')),
    ('P06/L2 private open follows a symlink (O_NOFOLLOW dropped)', 'full', 'L2', PFS,
     'return os.open(path, flags | os.O_NOFOLLOW | os.O_NONBLOCK, FILE_MODE)',
     'return os.open(path, flags | os.O_NONBLOCK, FILE_MODE)', pub('p20')),
    ('T10 trace: list items copied without the per-item shape check', 'full', 'L2', TC,
     'if not isinstance(value, list) or not all(check(item) for item in value):', 'if not isinstance(value, list):',
     pub('t10')),
    ('T10b trace: a list of records may hold anything', 'new', 'L2', TC,
     'if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):',
     'if not isinstance(value, list):', pub('t10')),
    ('T14 explain: selected without a handler execution', 'full', 'L2', TC,
     'if step["operation"] == "invoke" and step["handler_executed"] is True\n', 'if step["operation"] == "invoke"\n',
     pub('t14')),
    ('T15 explain: any policy verdict is the decision', 'full', 'L2', TC, ' and entry["verdict"] == "ALLOW"), None)',
     '), None)', pub('t14')),
    ('T16 explain: status of the selected step ignored', 'full', 'L2', TC, 'and step["status"] == "SUCCEEDED" and _is_ref',
     'and _is_ref', pub('t14')),
    ('T05 trace: events of another tenant shown', 'full', 'L2', TC,
     '                   and event.get("tenant_id") == self.context.tenant_id\n', '', pub('t05')),
    ('T06 trace: events of another actor shown', 'full', 'L2', TC,
     '                   and event.get("tenant_id") == self.context.tenant_id\n'
     '                   and event.get("actor_id") == self.context.actor_id]',
     '                   and event.get("tenant_id") == self.context.tenant_id]', pub('t05')),
    ('P17 trace reader tightens directories', 'full', 'L2', TS, 'state_directory(RECEIPTS, create=False, tighten=False)',
     'state_directory(RECEIPTS, create=False, tighten=True)', pub('p17')),
    ('S17 marker set gains a work word (please)', 'full', 'L1', SOC, 'MARKERS = frozenset(("urgent", ',
     'MARKERS = frozenset(("please", "urgent", ', unit('exactly or s17')),
    ('S17/L2 marker set gains a work word (please)', 'full', 'L2', SOC, 'MARKERS = frozenset(("urgent", ',
     'MARKERS = frozenset(("please", "urgent", ', pub('other_words')),
    ('S05c format characters are dropped inside and around a word', 'full', 'L1', SOC,
     '        character = folded[index]\n',
     '        character = folded[index]\n        if unicodedata.category(character) == "Cf" and character != ZERO_WIDTH_JOINER:\n'
     '            index += 1\n            continue\n', unit('s05c')),
    ('S05c/L2 format characters are dropped inside and around a word', 'full', 'L2', SOC,
     '        character = folded[index]\n',
     '        character = folded[index]\n        if unicodedata.category(character) == "Cf" and character != ZERO_WIDTH_JOINER:\n'
     '            index += 1\n            continue\n', pub('format_characters')),
    ('S05d the zero-width joiner is dropped between letters', 'new', 'L1', SOC,
     '        character = folded[index]\n',
     '        character = folded[index]\n        if character == ZERO_WIDTH_JOINER and current:\n'
     '            index += 1\n            continue\n', unit('s05c')),
    ('I05 owner uid not compared', 'full', 'L2', LI, "if signed['owner_uid'] != os.getuid() or key.public_key()",
     "if key.public_key()", pub('i05')),
    ('C05 asset locator: an assets FILE or symlink is accepted', 'full', 'L1', CT,
     'return packaged if packaged.is_dir() else checkout', 'return packaged if packaged.exists() else checkout',
     unit('c05')),
    ('S02b fold: single NFKC (before casefold only)', 'full', 'L1', SOC, FOLD,
     'folded = unicodedata.normalize("NFKC", text).casefold()', SOCIAL_L1),
    ('S12 a phrase belongs to the last language listing it', 'full', 'L1', SOC,
     'phrases.setdefault(words(phrase), (language, kind, template))', 'phrases[words(phrase)] = (language, kind, template)',
     SOCIAL_L1),
    ('S15 shortest phrase first', 'full', 'L1', SOC,
     'for size in range(min(MAX_PHRASE_WORDS, count - index), 0, -1):',
     'for size in range(1, min(MAX_PHRASE_WORDS, count - index) + 1):', SOCIAL_L1),
    ('P10b a writer tightens only when group or other bits are set', 'full', 'L1', PFS,
     '        elif mode != DIRECTORY_MODE:\n            os.fchmod(descriptor, DIRECTORY_MODE)',
     '        elif mode & 0o077:\n            os.fchmod(descriptor, DIRECTORY_MODE)',
     unit('p10b')),
    ('T03 trace: identifier shape not validated', 'full', 'L2', TC,
     'if not isinstance(identifier, str) or not (REQUEST_ID.fullmatch(identifier) or TRACE_ID.fullmatch(identifier)):',
     'if not isinstance(identifier, str):', [TRACE]),
    ('T04 trace: identifier prefix match', 'full', 'L2', TC,
     'not (REQUEST_ID.fullmatch(identifier) or TRACE_ID.fullmatch(identifier))',
     'not (REQUEST_ID.match(identifier) or TRACE_ID.match(identifier))', [TRACE]),
    ('T11 trace: receipt ids not shape-checked', 'full', 'L2', TC,
     '\n                and _is(REQUEST_ID, item["record"].get("request_id")) and _is(TRACE_ID, item["record"].get("trace_id"))]',
     ']', [TRACE]),
    ('X07 presentation boundary: exit without the shared rule', 'full', 'L2', C + 'main.py',
     'raise typer.Exit(settled_exit(code, value))', 'raise typer.Exit(code)',
     [MATRIX, PUB, '-k', 'x2 and audit or p19 or x6 or x06 or p17']),
    # ------------------------------------------------------------------ killed only in-process at a5a3af3 (l2.tsv)
    ('S06 urgency alone is social', 'l2', 'L2', SOC,
     '    if not found:\n        return None                                     # urgency alone',
     '    if not found:\n        return SocialMatch("en", DEFAULT_REPLY)', pub('urgency_alone')),
    ('P10 a reader accepts group or other bits', 'l2', 'L2', PFS,
     '            if mode & 0o077:\n                raise _refuse(path, "group or other permission bits")',
     '            if False:\n                raise _refuse(path, "group or other permission bits")', pub('p17')),
    ('P11 symlinked ancestor of the data directory accepted', 'l2', 'L2', PFS,
     'if any(ancestor.is_symlink() for ancestor in current.parents):', 'if False:', pub('p11')),
    ('P19 feature report save: directory chain not verified', 'l2', 'L2', FR,
     '        state_directory(self.root.name, root=self.root.parent)\n', '        self.root.mkdir(parents=True, exist_ok=True)\n',
     pub('p19')),
    ('P20 feature report pointer read follows a symlink', 'l2', 'L2', FR, 'pointer = json.loads(read_private(path) or b"")',
     'pointer = json.loads(path.read_bytes())', pub('p20')),
    ('P24 audit_events: plain read', 'l2', 'L2', CAP, 'return _events(read_private(self.audit_path) or b"")',
     'return _events(self.audit_path.read_bytes() if self.audit_path.exists() else b"")',
     [MATRIX, '-k', 'x2 and audit and (fifo or symlink_outside or mode_644)']),
    ('P32b probe: authentication before the configured check', 'l2', 'L2', CS,
     "        provider = data['provider']\n        if not provider['configured']:",
     "        provider = data['provider']\n        self.identity.authenticate()\n        if not provider['configured']:",
     pub('p32b')),
    ('X03 local store reasons: no audit_store_unavailable', 'l2', 'L2', DG, REASONS,
     'LOCAL_STORE_REASONS = ("audit_unavailable", "state_dir_unsafe",\n                       "feature_report_not_stored")',
     [MATRIX, TRACE, '-k', 'x2 and audit and symlink_outside or corrupted_audit or symlinked_receipt_file']),
    ('X03b local store reasons: no feature_report_not_stored', 'new', 'L2', DG, REASONS,
     'LOCAL_STORE_REASONS = ("audit_unavailable", "audit_store_unavailable", "state_dir_unsafe")', pub('p19')),
    ('X06 ask use case: exit without the shared rule', 'l2', 'L2', A + 'ask.py',
     'code = settled_exit(exit_code(value["status"], (value["error"] or {}).get("code")), value)',
     'code = exit_code(value["status"], (value["error"] or {}).get("code"))',
     [MATRIX, PUB, '-k', 'x2 and audit or x6 or x06 or p19']),
    ('I02 empty identifier accepted', 'l2', 'L2', LI, 'isinstance(signed.get(name), str) and ULID.fullmatch(signed[name])',
     'isinstance(signed.get(name), str) and (signed[name] == "" or ULID.fullmatch(signed[name]))', pub('i02')),
    ('I08 identity state shown inside a capability context', 'l2', 'L2', RF,
     'if os.environ.get("QUATI_CAPABILITY_CONTEXT"):      # a capability invocation is shown no credential state',
     'if False:', pub('i08')),
    # ------------------------------------------------------------------ this step's own changes
    ('E01 a removed language is still in the table (Spanish)', 'new', 'L2', SOC,
     '        THANKS: ("obrigado", "obrigada", "muito obrigado", "muito obrigada", "valeu"),\n    }),\n)',
     '        THANKS: ("obrigado", "obrigada", "muito obrigado", "muito obrigada", "valeu"),\n    }),\n'
     '    ("es", "Olá!", {GREETING: ("hola", "buenos días"), PLEASANTRY: ("qué tal",), THANKS: ("gracias",)}),\n)',
     pub('other_languages')),
    ('E02 a removed marker is still a marker (dringend)', 'new', 'L2', SOC, 'MARKERS = frozenset(("urgent", ',
     'MARKERS = frozenset(("dringend", "urgent", ', pub('other_languages')),
    ('E03 a removed urgency phrase is still listed (das ist dringend)', 'new', 'L2', SOC,
     '"isso é urgente", "é urgente")', '"isso é urgente", "é urgente", "das ist dringend")',
     [PUB, UNIT, '-k', 'other_languages or exactly']),
    ('D7a trace store refusal: exit 5', 'new', 'L2', TC, 'return settled_exit(5, value), value', 'return 5, value',
     [MATRIX, '-k', 'x2 and audit and symlink_outside']),
    # ------------------------------------------------------------------ harness graders (harness.tsv)
    ('H11 write: receipt-reported write execution accepted', 'harness', 'H', G,
     'not (set(results) | set(reported)) & WRITE_IDS', 'not set(results) & WRITE_IDS', HARNESS),
    ('H11b write: launched not checked', 'harness', 'H', G,
     "'no_model_text_displayed': not model_text_hits(value, receipt),\n        'launched_false': data.get('launched') is False,\n"
     "    }\n    return _graded(observation, checks, guard=guard",
     "'no_model_text_displayed': not model_text_hits(value, receipt),\n        'launched_false': True,\n"
     "    }\n    return _graded(observation, checks, guard=guard", HARNESS),
    ('H24 binding: unreadable receipt not failing', 'harness', 'H', G,
     "            counts['unreadable'] += 1\n            counts['failing'] += 1\n", "            counts['unreadable'] += 1\n", HARNESS),
    ('H28 selection: model identity not required', 'harness', 'H', LH,
     "'provider_identity_recorded': bool((receipt or {}).get('synthetic_evidence', {}).get('provider', {}).get('observed_model_ids')),",
     "'provider_identity_recorded': True,", HARNESS),
    ('H29 selection: status not checked', 'harness', 'H', LH,
     "'status_succeeded_no_error': value.get('status') == 'SUCCEEDED' and value.get('error') is None,",
     "'status_succeeded_no_error': True,", HARNESS),
    ('H30 selection: only-target rule off', 'harness', 'H', LH, "'only_target_executed': set(executed) == {target},",
     "'only_target_executed': target in executed,", HARNESS),
    ('H40 infra: a local-store refusal is a provider outage again', 'new', 'H', LH,
     "    if data.get('reason') in LOCAL_STORE_REASONS:\n        return None\n", '', HARNESS),
    ('H41 infra: a probe refused for a local store is a lost probe', 'new', 'H', LH,
     "\n                  and not (len(step) > 5 and step[5] in LOCAL_STORE_REASONS)]", ']', HARNESS),
    ('H42 evaluator copy of the local-store reasons diverges', 'new', 'H', LH,
     "'state_dir_unsafe', 'feature_report_not_stored')", "'state_dir_unsafe')", HARNESS),
    ('H43 asset locator: a packaged directory wins inside a checkout', 'new', 'H', G,
     "    if source.resolve().name == 'src' and (checkout / 'pyproject.toml').is_file() and all(\n"
     "            (checkout / name).is_dir() for name in ('contracts', 'examples')):\n        return root\n", '', HARNESS),
    ('H44 product asset digest: any field that holds "asset"', 'new', 'H', G, "value = (identity or {}).get('asset_digest')",
     "value = next((item for name, item in sorted((identity or {}).items()) if 'asset' in name), None)", HARNESS),
    ('H45 gate run without a product asset digest is not refused', 'new', 'H', G,
     "    elif registered_asset_digest(product) is None:", "    elif False:", HARNESS),
    ('H46 gate run with a differing asset digest is not refused', 'new', 'H', G,
     "    elif prereg.get('asset_tree_equals_product_asset_digest') is not True:", "    elif False:", HARNESS),
    # ------------------------------------------------------------------ checks that back each other (pairs)
    ('T03+T11 trace: neither the identifier nor the receipt ids are shape-checked', 'new', 'L2', TC,
     'if not isinstance(identifier, str) or not (REQUEST_ID.fullmatch(identifier) or TRACE_ID.fullmatch(identifier)):',
     'if not isinstance(identifier, str):', pub('t03'),
     [(TC, '\n                and _is(REQUEST_ID, item["record"].get("request_id")) and _is(TRACE_ID, item["record"].get("trace_id"))]',
       ']')]),
    ('T04+T11 trace: identifier matched by prefix and receipt ids not shape-checked', 'new', 'L2', TC,
     'not (REQUEST_ID.fullmatch(identifier) or TRACE_ID.fullmatch(identifier))',
     'not (REQUEST_ID.match(identifier) or TRACE_ID.match(identifier))', pub('t03'),
     [(TC, '\n                and _is(REQUEST_ID, item["record"].get("request_id")) and _is(TRACE_ID, item["record"].get("trace_id"))]',
       ']')]),
    ('X07+D7a exit rule applied neither by the trace use case nor at the boundary', 'new', 'L2', C + 'main.py',
     'raise typer.Exit(settled_exit(code, value))', 'raise typer.Exit(code)', [MATRIX, '-k', 'x2 and audit and symlink_outside'],
     [(TC, 'return settled_exit(5, value), value', 'return 5, value')]),
    ('X07+X06 exit rule applied neither by the ask use case nor at the boundary', 'new', 'L2', C + 'main.py',
     'raise typer.Exit(settled_exit(code, value))', 'raise typer.Exit(code)',
     pub('x06'),
     [(A + 'ask.py', 'code = settled_exit(exit_code(value["status"], (value["error"] or {}).get("code")), value)',
       'code = exit_code(value["status"], (value["error"] or {}).get("code"))')]),
    # ------------------------------------------------------------------ sanity
    ('Z00 sanity: the English reply text changed', 'new', 'L2', SOC, '    ("en", "Hello!", {', '    ("en", "Hullo!", {',
     pub('english_and_portuguese')),
]
COPIED = ('src', 'tests', 'examples', 'contracts', 'pyproject.toml', 'docs/implementation/SLICES', 'docs/testing',
          'evidence/S00/GATES-AUDIT3-2026-11-16/audit-scripts/d1_texts.py')


def run(mutant):
    label, origin, tier, relative, old, new, selection, *more = mutant
    edits = [(relative, old, new), *(more[0] if more else [])]
    mid = label.split()[0].replace('/', '-')
    target = SCRATCH / f'm-{mid}'
    shutil.rmtree(target, ignore_errors=True)
    for name in COPIED:
        source, destination = REPOSITORY / name, target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, destination, ignore=shutil.ignore_patterns('__pycache__'))
        else:
            shutil.copy2(source, destination)
    for relative, old, new in edits:
        path = target / relative
        source = path.read_text(encoding='utf-8')
        if source.count(old) != 1:
            shutil.rmtree(target, ignore_errors=True)
            return label, origin, tier, f'NOT_APPLIED({source.count(old)})', ''
        path.write_text(source.replace(old, new), encoding='utf-8')
    env = {k: v for k, v in os.environ.items() if not k.startswith('QUATI_') and k != 'PYTHONPATH'}
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    try:
        done = subprocess.run([str(PYTHON), '-m', 'pytest', '-q', '-x', '-p', 'no:cacheprovider', '--no-header', '--tb=no',
                               '-rf', *selection], cwd=target, env=env, capture_output=True, text=True, timeout=2400)
        lines = [line for line in done.stdout.splitlines() if line.strip()]
        failed = [line.split(' - ')[0].removeprefix('FAILED ') for line in lines if line.startswith(('FAILED', 'ERROR'))]
        verdict = 'KILLED' if done.returncode else 'SURVIVED'
        detail = failed[0] if failed else (lines[-1] if lines else '')
    except subprocess.TimeoutExpired:
        verdict, detail = 'KILLED', 'timeout (hang)'
    shutil.rmtree(target, ignore_errors=True)
    return label, origin, tier, verdict, detail


def main():
    selected = [m for m in MUTANTS if not ONLY or m[0].split()[0] in ONLY]
    ids = [m[0].split()[0] for m in MUTANTS]
    assert len(ids) == len(set(ids)), [i for i in ids if ids.count(i) > 1]
    SCRATCH.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=int(os.environ.get('MUTATE_WORKERS', '6'))) as pool:
        for label, origin, tier, verdict, detail in pool.map(run, selected):
            print(f'{verdict}\t{origin}\t{tier}\t{label}\t{detail}', flush=True)


main()
