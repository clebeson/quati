"""Mutation check for fix round 8 (X3, X4, X5/D7, SOC-01 timeout) on a scratch COPY of the repository.

Usage: python mutate.py REPO SCRATCH OUT. The repository itself is never modified: src/, tests/,
examples/, contracts/, pyproject.toml and the audit text list are copied to SCRATCH, each mutant is
applied to the copy, the selected tests run with the copy as pytest root, and the copy is restored.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO, SCRATCH, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
PYTHON = str(REPO / ".venv/bin/python")
UNIT = "tests/unit/test_s00_fix8_social_outcomes.py"
TIMEOUT = "tests/integration/cli/test_s00_fix8_social_timeout.py"
GATE = "tests/integration/test_approval_injection.py"
# The constants test is deselected so that every X4 kill below is a behavior test, not a comparison of constants.
TABLE = [UNIT, "-k", "x4 and not sample and not constants"]
D7 = [UNIT, "-k", "d7"]
K3 = [GATE, "-k", "composed_gate"]
SOCIAL = "src/quati/domain/social.py"
ASK = "src/quati/application/ask.py"
COMPOSITION = "src/quati/cli/composition.py"

MUTANTS = [
    # ---- X4 clause 1
    ("X4-1a", "clause 1: demonstratives and copulas are free-standing markers again", SOCIAL,
     'MARKERS = frozenset(("urgent", "urgently", "urgente", "dringend"))',
     'MARKERS = frozenset("urgent urgently urgente dringend this is it isto isso é esto c est das ist è questo".split())',
     TABLE),
    ("X4-1b", "clause 1: the words of an urgency phrase match one by one (not as a whole phrase)", SOCIAL,
     'URGENCY = frozenset(words(phrase) for phrase in URGENCY_PHRASES) | frozenset((marker,) for marker in MARKERS)',
     'URGENCY = frozenset((word,) for phrase in URGENCY_PHRASES for word in words(phrase)) | frozenset((marker,) for marker in MARKERS)',
     TABLE),
    ("X4-1c", "clause 1: the words of a table phrase match one by one (bag of words)", SOCIAL,
     '                phrases.setdefault(words(phrase), (language, kind, reply))',
     '                phrases.setdefault(words(phrase), (language, kind, reply))\n'
     '                for word in words(phrase):\n'
     '                    phrases.setdefault((word,), (language, kind, reply))',
     TABLE),
    ("X4-1d", "clause 1: urgency alone is social", SOCIAL,
     '    if not found:\n        return None                                     # urgency alone',
     '    if not found:\n        return SocialMatch("en", DEFAULT_REPLY)',
     TABLE),
    ("X4-1e", "clause 1: an urgency phrase is removed (\"es ist dringend\")", SOCIAL,
     '"das ist dringend", "es ist dringend", "è urgente"', '"das ist dringend", "è urgente"', TABLE),
    ("X4-1f", "clause 1: a new marker word is added (\"please\")", SOCIAL,
     'MARKERS = frozenset(("urgent", "urgently", "urgente", "dringend"))',
     'MARKERS = frozenset(("urgent", "urgently", "urgente", "dringend", "please"))', TABLE),
    # ---- X4 clause 2
    ("X4-2a", "clause 2: Italian `salve` is back in the table", SOCIAL,
     'GREETING: ("ciao", "buongiorno", "buonasera"),', 'GREETING: ("ciao", "buongiorno", "buonasera", "salve"),', TABLE),
    # ---- X4 clause 3
    ("X4-3a", "clause 3: a character the rule does not name is dropped as a separator", SOCIAL,
     '            return None            # a character the rule does not name is never silently dropped',
     '            run_length = 0', TABLE),
    ("X4-3b", "clause 3: every Unicode punctuation character is accepted", SOCIAL,
     '        elif character in PUNCTUATION:', '        elif unicodedata.category(character)[0] == "P":', TABLE),
    ("X4-3c", "clause 3: every symbol is accepted as an emoji (no allowlist)", SOCIAL,
     '        if character in EMOJI:\n            index = _emoji_end(folded, index)',
     '        if character in EMOJI or unicodedata.category(character) == "So":\n            index = _emoji_end(folded, index)',
     TABLE),
    ("X4-3d", "clause 3: no emoji is accepted (\"hello\" plus a heart is not social)", SOCIAL,
     '        if character in EMOJI:\n            index = _emoji_end(folded, index)',
     '        if False:\n            index = _emoji_end(folded, index)', TABLE),
    ("X4-3e", "clause 3: one emoji is removed from the allowlist (the heart)", SOCIAL,
     '"\\U0001F64F\\u2764")', '"\\U0001F64F")', TABLE),
    ("X4-3f", "clause 3: U+200D after an emoji is accepted whatever follows", SOCIAL,
     'text[index] == ZERO_WIDTH_JOINER and text[index + 1] in EMOJI', 'text[index] == ZERO_WIDTH_JOINER', TABLE),
    ("X4-3g", "clause 3: several modifiers may follow one emoji", SOCIAL,
     '        if index < len(text) and (text[index] == VARIATION_SELECTOR or text[index] in SKIN_TONES):',
     '        while index < len(text) and (text[index] == VARIATION_SELECTOR or text[index] in SKIN_TONES):', TABLE),
    ("X4-3h", "clause 3: U+FE0F and skin tones are not accepted after an emoji", SOCIAL,
     '        if index < len(text) and (text[index] == VARIATION_SELECTOR or text[index] in SKIN_TONES):',
     '        if False:', TABLE),
    ("X4-3i", "clause 3: any number of free punctuation runs between two words (Morse)", SOCIAL,
     '            and len(runs) - min(attached, len(runs)) <= MAX_FREE_PUNCTUATION_RUNS)', '            and True)', TABLE),
    ("X4-3j", "clause 3: a punctuation run of any length", SOCIAL,
     '    return (all(len(run) <= MAX_PUNCTUATION_RUN for run in runs)\n            and', '    return (True\n            and', TABLE),
    ("X4-3k", "clause 3: an emoji does not end a punctuation run", SOCIAL,
     '            index = _emoji_end(folded, index)\n            gap.append(" ")',
     '            index = _emoji_end(folded, index)', TABLE),
    ("X4-3l", "clause 3: every run is free (closing and opening punctuation of two sentences is refused)", SOCIAL,
     '    attached = int(after_word and gap.startswith("p")) + int(before_word and gap.endswith("p"))',
     '    attached = 0', TABLE),
    ("X4-3l2", "clause 3: two free runs are allowed", SOCIAL,
     'MAX_FREE_PUNCTUATION_RUNS = 1', 'MAX_FREE_PUNCTUATION_RUNS = 2', TABLE),
    ("X4-3l3", "clause 3: a run at the start of the text counts as attached to a word before it", SOCIAL,
     '            if not current and not _gap_allowed("".join(gap), bool(found), True):',
     '            if not current and not _gap_allowed("".join(gap), True, True):', TABLE),
    ("X4-3l4", "clause 3: a run at the end of the text counts as attached to a word after it", SOCIAL,
     '    if not _gap_allowed("".join(gap), bool(found), False) or len(found) > MAX_SOCIAL_WORDS:',
     '    if not _gap_allowed("".join(gap), bool(found), True) or len(found) > MAX_SOCIAL_WORDS:', TABLE),
    ("X4-3l5", "clause 3: the gap after the last word is not checked", SOCIAL,
     '    if not _gap_allowed("".join(gap), bool(found), False) or len(found) > MAX_SOCIAL_WORDS:',
     '    if len(found) > MAX_SOCIAL_WORDS:', TABLE),
    ("X4-3l6", "clause 3: the run length bound is 4", SOCIAL, 'MAX_PUNCTUATION_RUN = 3', 'MAX_PUNCTUATION_RUN = 4', TABLE),
    ("X4-3m", "clause 3: every Unicode space and control separator is whitespace", SOCIAL,
     '        if character in WHITESPACE or unicodedata.category(character) == "Zs":',
     '        if character.isspace() or unicodedata.category(character)[0] == "Z":', TABLE),
    ("X4-3n", "clause 3: tab and line breaks are not whitespace", SOCIAL,
     '        if character in WHITESPACE or unicodedata.category(character) == "Zs":',
     '        if unicodedata.category(character) == "Zs":', TABLE),
    ("X4-3o", "clause 3: combining marks split words (they are separators, not word characters)", SOCIAL,
     [('        if unicodedata.category(character)[0] in "LMN":', '        if unicodedata.category(character)[0] in "LN":'),
      ('        if character in WHITESPACE or unicodedata.category(character) == "Zs":',
       '        if character in WHITESPACE or unicodedata.category(character) in ("Zs", "Mn", "Mc", "Me"):')], None, TABLE),
    ("X4-3p", "clause 3: numbers are separators, not words", SOCIAL,
     [('        if unicodedata.category(character)[0] in "LMN":', '        if unicodedata.category(character)[0] in "LM":'),
      ('        if character in WHITESPACE or unicodedata.category(character) == "Zs":',
       '        if character in WHITESPACE or unicodedata.category(character) in ("Zs", "Nd", "Nl", "No"):')], None, TABLE),
    ("X4-3q", "clause 3: one punctuation character is removed from the set (the Arabic question mark)", SOCIAL,
     '"،؛؟"', '"،؛"', TABLE),
    ("X4-3r", "clause 3: the text is matched without NFKC (compatibility letters are not folded)", SOCIAL,
     '    folded = unicodedata.normalize("NFKC", unicodedata.normalize("NFKC", text).casefold())',
     '    folded = text.casefold()', TABLE),
    # ---- X4 clause 4
    ("X4-4a", "clause 4: no bound in words", SOCIAL,
     '    if not _gap_allowed("".join(gap), bool(found), False) or len(found) > MAX_SOCIAL_WORDS:',
     '    if not _gap_allowed("".join(gap), bool(found), False):', TABLE),
    ("X4-4b", "clause 4: no bound in characters", SOCIAL,
     '    if len(folded) > MAX_SOCIAL_CHARACTERS:\n        return None', '', TABLE),
    ("X4-4c", "clause 4: the character bound is measured before normalization", SOCIAL,
     '    if len(folded) > MAX_SOCIAL_CHARACTERS:', '    if len(text) > MAX_SOCIAL_CHARACTERS:', TABLE),
    ("X4-4d", "clause 4: the word bound is 13", SOCIAL, 'MAX_SOCIAL_WORDS = 12', 'MAX_SOCIAL_WORDS = 13', TABLE),
    ("X4-4e", "clause 4: the character bound is 121", SOCIAL, 'MAX_SOCIAL_CHARACTERS = 120', 'MAX_SOCIAL_CHARACTERS = 121',
     TABLE),
    # ---- X4 on the public path
    ("X4-5a", "public path: the social answer is never given (every text goes to the model path)", ASK,
     '    found = social_match(text)\n    if found is None:', '    found = None\n    if found is None:',
     [UNIT, "-k", "sample"]),
    ("X4-5b", "public path: demonstratives are markers again (the audit's texts are greetings in ask and chat)", SOCIAL,
     'MARKERS = frozenset(("urgent", "urgently", "urgente", "dringend"))',
     'MARKERS = frozenset("urgent urgently urgente dringend this is it isto isso é esto c est das ist è questo".split())',
     [UNIT, "-k", "sample"]),
    ("X4-5c", "public path: unnamed characters are dropped (the audit's enclosed-letter texts are greetings)", SOCIAL,
     '            return None            # a character the rule does not name is never silently dropped',
     '            run_length = 0', [UNIT, "-k", "sample"]),
    # ---- X5 / D7
    ("D7-a", "NO_CAPABILITY is SUCCEEDED again", ASK,
     '        return _envelope_response("UNAVAILABLE", data, "UNSUPPORTED", NO_CAPABILITY_MESSAGE,\n'
     '                                  NO_CAPABILITY_NEXT_ACTION, ["NO_CAPABILITY", reason])',
     '        return _envelope_response("SUCCEEDED", data, None, None, "report_no_capability", ["NO_CAPABILITY", reason])',
     D7),
    ("D7-b", "NO_CAPABILITY is PARTIAL (still exit 0)", ASK,
     '        return _envelope_response("UNAVAILABLE", data, "UNSUPPORTED", NO_CAPABILITY_MESSAGE,',
     '        return _envelope_response("PARTIAL", data, "UNSUPPORTED", NO_CAPABILITY_MESSAGE,', D7),
    ("D7-c", "NO_CAPABILITY uses another status and code (BLOCKED / EVIDENCE_INSUFFICIENT)", ASK,
     '        return _envelope_response("UNAVAILABLE", data, "UNSUPPORTED", NO_CAPABILITY_MESSAGE,',
     '        return _envelope_response("BLOCKED", data, "EVIDENCE_INSUFFICIENT", NO_CAPABILITY_MESSAGE,', D7),
    ("D7-d", "NO_CAPABILITY is a provider failure (exit 5)", ASK,
     '        return _envelope_response("UNAVAILABLE", data, "UNSUPPORTED", NO_CAPABILITY_MESSAGE,',
     '        return _envelope_response("UNAVAILABLE", data, "TEMPORARILY_UNAVAILABLE", NO_CAPABILITY_MESSAGE,', D7),
    ("D7-e", "the result kind is no longer NO_CAPABILITY", ASK,
     '        data = self.data("NO_CAPABILITY", result_status="NO_CAPABILITY", reason=reason, outcome="NO_CAPABILITY",',
     '        data = self.data("BLOCKED", result_status="NO_CAPABILITY", reason=reason, outcome="NO_CAPABILITY",', D7),
    ("D7-f", "work_performed is not reported", ASK,
     'outcome="NO_CAPABILITY",\n                         work_performed=False)', 'outcome="NO_CAPABILITY")', D7),
    ("D7-g", "the next_action is the old token", ASK,
     '                                  NO_CAPABILITY_NEXT_ACTION, ["NO_CAPABILITY", reason])',
     '                                  "report_no_capability", ["NO_CAPABILITY", reason])', D7),
    ("D7-h", "an empty search is NO_VERIFIED_EXECUTION instead of NO_CAPABILITY", ASK,
     '        if searches and not any(step["candidate_ids"] for step in searches):',
     '        if False:', D7),
    ("D7-i", "NONE_FITS wins over a validated execution (FIXTURE_RESULT is no longer a success)", ASK,
     '        succeeded = self.fixture_results("SUCCEEDED")\n        if succeeded:',
     '        succeeded = self.fixture_results("SUCCEEDED")\n'
     '        if succeeded and not any(step["operation"] == "none_fits" for step, _ in self.steps):', D7),
    ("D7-j", "a model text with no execution is a success (NO_VERIFIED_EXECUTION becomes SUCCEEDED)", ASK,
     '        return _envelope_response("BLOCKED", self.data("BLOCKED", reason="NO_VERIFIED_EXECUTION"),\n'
     '                                  "EVIDENCE_INSUFFICIENT", "No capability was executed and validated.",',
     '        return _envelope_response("SUCCEEDED", self.data("BLOCKED", reason="NO_VERIFIED_EXECUTION"),\n'
     '                                  None, "No capability was executed and validated.",', D7),
    ("D7-k", "the uncertainties lose the reason", ASK,
     'NO_CAPABILITY_NEXT_ACTION, ["NO_CAPABILITY", reason])', 'NO_CAPABILITY_NEXT_ACTION, ["NO_CAPABILITY"])', D7),
    # ---- X3
    ("X3-a", "the audit's mutant: the composition root composes the S02 runtime profile", COMPOSITION,
     'RUNTIME_PROFILE = "S00"', 'RUNTIME_PROFILE = "S02"', K3),
    ("X3-b", "the composed gate ignores RUNTIME_PROFILE and passes S02", COMPOSITION,
     '                                           runtime_profile=RUNTIME_PROFILE)',
     '                                           runtime_profile="S02")', K3),
    ("X3-c", "ask_runtime builds its own gate (S02) instead of using policy_gate", COMPOSITION,
     '    gate = policy_gate(identity, context, clock=clock, ids=ids)',
     '    gate = LocalPolicyGate.from_config_dir(identity.directory, tenant_id=context.tenant_id,\n'
     '                                           installation_uid=os.getuid(), clock=clock, ids=ids, directory=identity,\n'
     '                                           runtime_profile="S02")', K3),
    ("X3-d", "the public policy_gate function composes S02 while ask_runtime keeps S00", COMPOSITION,
     '    gate = policy_gate(identity, context, clock=clock, ids=ids)',
     '    gate = policy_gate(identity, context, clock=clock, ids=ids)\n    gate.runtime_profile = "S00"\n'
     '    globals()["RUNTIME_PROFILE"] = "S02"', K3),
    ("X3-e", "the composed gate allows every effect (a gate that is not the trusted policy gate)", COMPOSITION,
     '    gate = policy_gate(identity, context, clock=clock, ids=ids)',
     '    gate = policy_gate(identity, context, clock=clock, ids=ids)\n'
     '    gate.decide = lambda context, intent, runtime_profile=None: LocalPolicyGate.decide(gate, context, intent, "S02")',
     K3),
    # ---- SOC-01 timeout at L2
    ("T-a", "a model timeout on the classification falls back to a social success", ASK,
     '        except ProviderError as exc:\n            return self.finish(self.provider_failure(exc), envelope)',
     '        except ProviderError as exc:\n'
     '            return self.finish(_envelope_response("SUCCEEDED", self.data("GREETING", text="Hello!")), envelope)',
     [TIMEOUT]),
    ("T-b", "a provider timeout is reported as launched work", ASK,
     '                "launched": False, "delivered": False, "feature_support": self.gate["tools"],',
     '                "launched": bool(self.model_calls), "delivered": False, "feature_support": self.gate["tools"],',
     [TIMEOUT]),
    ("T-c", "after a timeout the classification is retried (the obedient model then executes)", ASK,
     '                if exc.code != "OUTPUT_INVALID":\n                    raise',
     '                if exc.code not in ("OUTPUT_INVALID", "DEADLINE_EXCEEDED"):\n                    raise', [TIMEOUT]),
    ("T-d", "a timeout is a local refusal (exit 4, BLOCKED EVIDENCE_INSUFFICIENT) instead of the provider failure", ASK,
     '        return _envelope_response(status, self.data("BLOCKED", reason=exc.reason), exc.code, message, next_action,',
     '        return _envelope_response(status, self.data("BLOCKED", reason=exc.reason), "EVIDENCE_INSUFFICIENT", message, next_action,',
     [TIMEOUT]),
    ("T-e", "a table greeting is answered only after the model path (the timeout reaches it)", ASK,
     '    found = social_match(text)\n    if found is None:', '    found = None\n    if found is None:', [TIMEOUT]),
]


def copy_tree():
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    SCRATCH.mkdir(parents=True)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    for name in ("src", "tests", "examples", "contracts"):
        shutil.copytree(REPO / name, SCRATCH / name, ignore=ignore)
    shutil.copy(REPO / "pyproject.toml", SCRATCH / "pyproject.toml")
    audit = "evidence/S00/GATES-AUDIT3-2026-11-16/audit-scripts/d1_texts.py"
    (SCRATCH / audit).parent.mkdir(parents=True)
    shutil.copy(REPO / audit, SCRATCH / audit)


def run(selection):
    done = subprocess.run([PYTHON, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-x", "--tb=no", "-rf", *selection],
                          cwd=SCRATCH, capture_output=True, text=True, timeout=1800,
                          env={"PATH": "/usr/bin:/bin", "HOME": str(SCRATCH / "home"), "PYTHONDONTWRITEBYTECODE": "1"})
    lines = [line for line in done.stdout.splitlines() if line.strip()]
    failed = next((line for line in lines if line.startswith("FAILED")), "")
    failed = re.sub(r" - .*", "", failed)
    return done.returncode, failed, lines[-1] if lines else done.stderr[-300:]


def main():
    copy_tree()
    for name, _title, path, old, new, _selection in MUTANTS:          # every mutant applies exactly once
        text = (SCRATCH / path).read_text(encoding="utf-8")
        for before, _after in (old if isinstance(old, list) else [(old, new)]):
            assert text.count(before) == 1, (name, before, text.count(before))
    if len(sys.argv) > 4:
        return
    out = ["Mutation check for fix round 8 (LOG-0044: X3, X4, X5 / D7, SOC-01 timeout at L2).",
           "Every mutant is applied to a scratch COPY of src/ (the repository is never modified), one at a time;",
           "the selected fix round 8 tests run with pytest -x against the copy (children import the copy).",
           "KILLED = pytest exit 1 with a failing test (or exit 2 when the mutant cannot even be imported);",
           "SURVIVED = exit 0. For the table mutants the test that compares the rule constants with the contract",
           "(test_x4_rule_constants_are_exactly_the_contract) is deselected, so each kill is a behavior test.", ""]
    code, _failed, last = run([UNIT, TIMEOUT, GATE, "-k", "x4 or d7 or soc_01 or composed_gate"])
    where = subprocess.run([PYTHON, "-c", "import quati, pathlib; print(pathlib.Path(quati.__file__).resolve())"],
                           cwd=SCRATCH, capture_output=True, text=True,
                           env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(SCRATCH / "src")}).stdout.strip()
    assert where.startswith(str(SCRATCH)), where
    out.append(f"baseline (no mutant, scratch copy): pytest exit {code}: {last}")
    assert code == 0, last
    killed = 0
    for name, title, path, old, new, selection in MUTANTS:
        target = SCRATCH / path
        original = target.read_text(encoding="utf-8")
        mutated = original
        for before, after in (old if isinstance(old, list) else [(old, new)]):
            assert mutated.count(before) == 1, (name, mutated.count(before))
            mutated = mutated.replace(before, after)
        target.write_text(mutated, encoding="utf-8")
        try:
            code, failed, last = run(selection)
        finally:
            target.write_text(original, encoding="utf-8")
        if code == 1 and failed:
            verdict = "KILLED"
        elif code == 2 and "error" in last:
            verdict = "KILLED (collection error: the mutant breaks the import of quati.domain.social)"
        else:
            verdict = f"SURVIVED (pytest exit {code})"
        killed += verdict.startswith("KILLED")
        out += [f"mutant {name}: {title}", f"   file: {path}", f"   tests: {' '.join(selection)}",
                f"   -> {verdict}; {failed} | {last}"]
        print(out[-4], out[-1], flush=True)
    out += ["", f"{killed} of {len(MUTANTS)} mutants killed."]
    text = "\n".join(out) + "\n"
    text = text.replace(str(SCRATCH), "<scratch>").replace(str(REPO), "<repo>")
    OUT.write_text(text, encoding="utf-8")
    print(out[-1])


main()
