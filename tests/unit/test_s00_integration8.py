"""S00 integration step 8: L1 tests for the gaps of the third audit, part 3 (LOG-0045) and the owner
decision of 2026-11-16 (the S00 social table supports English and Portuguese only).

Proof tier L1: pure domain functions and one storage adapter on an isolated temporary directory. The
public behavior of the same rules is proven in child processes by
tests/integration/cli/test_s00_integration8_public.py. No network, no provider, no clock.

* SOC-01 / S00 runtime contract rule 2: the table is exactly the English and Portuguese entries below;
  a text of any other language, urgency alone and a word that holds a format character are not social.
* M01 "Data directory" rule 2: the registry lock file is opened through the private-file helper (audit
  mutants P23, P23b, P06), whatever was verified by name before.
* M01 exit table rows 4 and 5: one list of local-store reasons decides exit 4.
* LOG-0044 D7: no helper builds a SUCCEEDED "no capability" answer.
"""

from __future__ import annotations

import os
import unicodedata
from pathlib import Path

import pytest

from quati.adapters import private_fs
from quati.adapters.capability_store import FileRegistryStore, empty_state
from quati.adapters.private_fs import UnsafeStatePath
from quati.domain import diagnostics, social

# ----------------------------------------------------------------- the social table, restated in full
EXPECTED_TABLE = (
    ("en", "Hello!", {
        "greeting": ("hello", "hi", "hey", "hello there", "hi there", "hey there", "good morning", "good afternoon",
                     "good evening", "good day", "howdy", "hiya", "greetings", "yo"),
        "pleasantry": ("how are you", "how are you doing", "how are you today", "how are you doing today",
                       "how is it going", "how's it going", "how do you do", "what's up", "whats up"),
        "thanks": ("thanks", "thank you", "thanks a lot", "many thanks", "thank you very much"),
    }),
    ("pt", "Olá!", {
        "greeting": ("olá", "ola", "oi", "bom dia", "boa tarde", "boa noite"),
        "pleasantry": ("tudo bem", "tudo bom", "tudo bem com você", "tudo bem com voce", "como vai", "como vai você",
                       "como vai voce", "como você está", "como voce esta", "como está", "e você", "e voce", "e aí",
                       "e ai"),
        "thanks": ("obrigado", "obrigada", "muito obrigado", "muito obrigada", "valeu"),
    }),
)
EXPECTED_MARKERS = {"urgent", "urgently", "urgente"}
EXPECTED_URGENCY_PHRASES = {"this is urgent", "it is urgent", "isto é urgente", "isso é urgente", "é urgente"}
# Samples of every language the table held before the owner decision, and of some it never held.
OTHER_LANGUAGES = {
    "es": ["hola", "¡Hola! ¿Qué tal?", "buenos días", "buenas", "qué tal", "gracias", "muchas gracias"],
    "fr": ["bonjour", "bonsoir", "salut", "coucou", "ça va", "merci", "merci beaucoup", "c'est urgent, bonjour"],
    "de": ["hallo", "guten tag", "guten morgen", "moin", "servus", "grüß gott", "wie geht es dir", "danke",
           "vielen dank", "das ist dringend, hallo", "es ist dringend. Danke!", "hello, dringend"],
    "it": ["ciao", "buongiorno", "buonasera", "come stai", "grazie", "ciao, è urgente", "hello, questo è urgente"],
    "nl": ["hoi", "goedemorgen", "hoe gaat het", "bedankt", "dank je wel"],
    "tr": ["merhaba", "selam", "günaydın", "günaydin", "İyi günler", "teşekkürler"],
    "ru": ["привет", "здравствуйте", "как дела", "спасибо"],
    "ja": ["こんにちは", "おはよう", "ありがとう", "konnichiwa"],
    "zh": ["你好", "您好", "谢谢", "ni hao"],
    "ko": ["안녕하세요", "감사합니다"],
    "hi": ["नमस्ते", "namaste", "धन्यवाद"],
    "ar": ["مرحبا", "السلام عليكم", "شكرا"],
    "never_listed": ["sawubona", "hyvää päivää", "moikka", "kia ora", "aloha", "hej", "tack"],
}
FORMAT_CHARACTERS = ("​", "‌", "‍", "⁠", "﻿", "­", "‎", "‮", "⁦", "؜")


def test_e_the_social_table_is_exactly_the_english_and_portuguese_entries():
    """Owner decision of 2026-11-16: S00 supports English and Portuguese only; other languages are deferred."""
    assert social.SOCIAL_TABLE == EXPECTED_TABLE
    assert {language for language, _template, _kinds in social.SOCIAL_TABLE} == {"en", "pt"}
    assert set(social.MARKERS) == EXPECTED_MARKERS
    assert set(social.URGENCY_PHRASES) == EXPECTED_URGENCY_PHRASES and len(social.URGENCY_PHRASES) == 5
    assert social.DEFAULT_REPLY == "Hello!"                              # English is the fallback
    assert {reply for _language, _kind, reply in social.PHRASES.values()} == {"Hello!", "Olá!"}
    assert {language for language, _kind, _reply in social.PHRASES.values()} == {"en", "pt"}
    assert not hasattr(social, "GREETING_REPLIES")                       # no greeting of a removed language is left
    listed = [phrase for _language, _template, kinds in EXPECTED_TABLE for phrases in kinds.values() for phrase in phrases]
    assert len(social.PHRASES) == len(listed) == len(set(listed))        # every entry is a phrase of its own


@pytest.mark.parametrize("language", sorted(OTHER_LANGUAGES))
def test_e_text_of_any_other_language_is_not_social_only(language):
    for text in OTHER_LANGUAGES[language]:
        for variant in (text, text.upper(), f"{text}!", f"{text}, urgent", f"hello, {text}", f"{text}, obrigado"):
            assert social.social_match(variant) is None, variant


def test_e_english_and_portuguese_replies_are_unchanged():
    for text, language, reply in (("Hello!", "en", "Hello!"), ("thanks", "en", "Hello!"), ("How do you do?", "en", "Hello!"),
                                  ("Olá, tudo bem?", "pt", "Olá!"), ("obrigada", "pt", "Olá!"), ("BOM DIA", "pt", "Olá!"),
                                  ("thanks, bom dia", "pt", "Olá!"), ("bom dia, hello", "pt", "Olá!"),
                                  ("valeu, hello", "en", "Hello!"), ("urgente: oi", "pt", "Olá!"),
                                  ("hello, isto é urgente", "en", "Hello!")):
        found = social.social_match(text)
        assert found is not None and (found.language, found.reply) == (language, reply), text


# ----------------------------------------------------------------- S05c, S17: format characters and markers
def test_s05c_a_format_character_inside_or_around_any_table_word_makes_the_text_not_social():
    """A zero-width or other format character (general category Cf) is never dropped: not inside a word,
    not before it, not after it, not in a marker or an urgency phrase."""
    assert all(unicodedata.category(character) == "Cf" for character in FORMAT_CHARACTERS)
    phrases = [phrase for _language, _template, kinds in social.SOCIAL_TABLE for listed in kinds.values() for phrase in listed]
    for phrase in phrases:
        assert social.social_match(phrase) is not None, phrase
        for character in FORMAT_CHARACTERS:
            for position in range(len(phrase) + 1):
                broken = phrase[:position] + character + phrase[position:]
                assert social.social_match(broken) is None, ascii(broken)
    for urgency in [*EXPECTED_MARKERS, *EXPECTED_URGENCY_PHRASES]:
        assert social.social_match(f"hello, {urgency}") is not None, urgency
        for character in FORMAT_CHARACTERS:
            for position in range(len(urgency) + 1):
                broken = f"hello, {urgency[:position]}{character}{urgency[position:]}"
                assert social.social_match(broken) is None, ascii(broken)


@pytest.mark.parametrize("word", ["please", "por favor", "now", "agora", "asap", "today", "hoje", "ok", "yes", "sim",
                                  "dringend", "urgentemente", "important", "importante"])
def test_s17_no_other_word_is_an_urgency_marker(word):
    """The marker set is closed: a politeness, time or assent word next to a greeting is not social."""
    for text in (f"hello, {word}", f"{word}, hello", f"olá, {word}", f"hello {word} thanks"):
        assert social.social_match(text) is None, text
    assert social.social_match(word) is None


# ----------------------------------------------------------------- P23, P23b, P06: the registry lock file
def committed_store(tmp_path: Path) -> tuple[FileRegistryStore, Path]:
    root = tmp_path / "data" / "capabilities"
    FileRegistryStore(root).commit(empty_state(), expected_revision=0)
    assert (root / "registry.flock").is_file()
    return FileRegistryStore(root), root / "registry.flock"       # a new instance: nothing verified by name yet


def break_lock(lock: Path, outside: Path, kind: str) -> None:
    if kind == "symlink":
        victim = outside / "victim"
        victim.write_bytes(b"outside")
        victim.chmod(0o600)
        lock.unlink()
        lock.symlink_to(victim)
    elif kind == "directory":
        lock.unlink()
        lock.mkdir(mode=0o700)
    elif kind == "fifo":
        lock.unlink()
        os.mkfifo(lock, 0o600)
    elif kind == "hard_link":
        os.link(lock, outside / "second-name")
    else:
        lock.chmod(0o644)


@pytest.mark.parametrize("kind", ["symlink", "directory", "fifo", "hard_link", "mode_0644", "foreign_owner"])
def test_p23_the_registry_lock_file_is_opened_as_a_private_file_or_not_at_all(tmp_path, monkeypatch, kind):
    """M01 "Data directory" rule 2 at the adapter: the descriptor check of the lock file is the authority.
    ``prepare`` (the check by name that the commands run first) is deliberately NOT called, so only the
    open of the lock itself can refuse. Nothing is committed, nothing outside is touched and the mode of a
    permissive lock file is not repaired."""
    outside = tmp_path / "outside"
    outside.mkdir()
    store, lock = committed_store(tmp_path)
    registry = store.registry_path.read_bytes()
    if kind == "foreign_owner":
        real, inode = os.fstat, lock.stat().st_ino

        class Foreign:
            def __init__(self, info):
                self._info = info

            def __getattr__(self, name):
                return os.getuid() + 1 if name == "st_uid" else getattr(self._info, name)

        monkeypatch.setattr(private_fs.os, "fstat", lambda descriptor: (
            Foreign(real(descriptor)) if real(descriptor).st_ino == inode else real(descriptor)))
    else:
        break_lock(lock, outside, kind)
    for change in (lambda: store.commit(empty_state(), expected_revision=1),
                   lambda: store.write_lock_entry({"id": "fixtures.x", "version": "1.0.0"})):
        with pytest.raises(UnsafeStatePath) as refused:
            change()
        assert refused.value.filename == str(lock)
    assert store.registry_path.read_bytes() == registry and not store.lock_path.exists()
    if kind == "symlink":
        assert (outside / "victim").read_bytes() == b"outside" and lock.is_symlink()
    if kind == "mode_0644":
        assert lock.stat().st_mode & 0o777 == 0o644              # refused, never repaired


# ----------------------------------------------------------------- exit rule: one list of local-store reasons
def test_local_store_reasons_are_the_documented_list_and_each_settles_exit_4():
    """M01 "Exit codes (stable)" rows 4 and 5: UNAVAILABLE whose reason names a local store exits 4."""
    assert diagnostics.LOCAL_STORE_REASONS == (
        "audit_unavailable", "audit_store_unavailable", "state_dir_unsafe", "feature_report_not_stored")
    from quati.cli.rendering import exit_code
    for reason in diagnostics.LOCAL_STORE_REASONS:
        value = {"status": "UNAVAILABLE", "data": {"reason": reason}, "error": {"code": "TEMPORARILY_UNAVAILABLE"}}
        assert diagnostics.settled_exit(5, value) == 4 and exit_code(value) == 4, reason
    provider = {"status": "UNAVAILABLE", "data": {"reason": "CLI_FAILED"}, "error": {"code": "TEMPORARILY_UNAVAILABLE"}}
    assert diagnostics.settled_exit(5, provider) == 5 and exit_code(provider) == 5


# ----------------------------------------------------------------- D7: no SUCCEEDED "no capability" helper
def test_d7_no_helper_builds_a_succeeded_no_capability_answer():
    from quati.application import discovery_tools
    assert not hasattr(discovery_tools, "honest_no_capability")
    assert "honest_no_capability" not in discovery_tools.__all__


# ----------------------------------------------------------------- C05: the packaged asset directory
def test_c05_only_a_real_assets_directory_is_the_packaged_asset_root(tmp_path):
    """behavior/contracts.py ``asset_root`` outside a source checkout: ``<package>/assets`` is used only
    when it is a directory. A regular file of that name (or a link to one) is not an asset root; the
    fallback is the directory two levels above the package."""
    from quati.behavior import contracts
    package = tmp_path / "site-packages" / "quati"
    package.mkdir(parents=True)
    fallback = package.resolve().parents[1]
    assert contracts.asset_root(package) == fallback
    (package / "assets").write_text("not a directory", encoding="utf-8")
    assert contracts.asset_root(package) == fallback
    (package / "assets").unlink()
    (tmp_path / "a-file").write_text("x", encoding="utf-8")
    (package / "assets").symlink_to(tmp_path / "a-file")
    assert contracts.asset_root(package) == fallback
    (package / "assets").unlink()
    (package / "assets").mkdir()
    assert contracts.asset_root(package) == package / "assets"


# ----------------------------------------------------------------- a refused step reads no registry
def test_a_tool_step_refused_before_any_registry_lookup_does_not_read_the_catalog(tmp_path):
    """S00 runtime contract (decision D4: "the registry is not consulted" for an id outside the shortlist),
    M15 invoke guard table and M02 authorization order row 7 (a denied caller causes no registry access):
    building the trajectory step of a refused tool call must not read the registry either. Only a step
    for which trusted code already resolved a registry entry is checked against the catalog."""
    import json
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from s00_t03_support import build
    from quati.application.discovery_tools import execute_tool_call
    from quati.application.providers import ToolCall
    from quati.domain.canonical import digest

    harness = build(tmp_path)
    harness.install("mail-search")
    turn = harness.turn()
    registry, reads = turn.service.registry, []
    real_catalog = registry.catalog
    registry.catalog = lambda context: (reads.append(context.request_id), real_catalog(context))[1]
    execute_tool_call(turn, turn.context, ToolCall("quati_search", {"query": "search my email messages"}))
    assert list(turn.shortlist) == ["fixtures.mail-search"] and reads
    for supplied in ("fixtures.does-not-exist", "fixtures.calendar-read", "Not A Capability Id!"):
        before = len(reads)
        text, step = execute_tool_call(turn, turn.context, ToolCall("quati_invoke", {"capability_id": supplied, "input": {}}))
        assert (step["status"], step["reason"], step["handler_executed"]) == ("DENIED", "NOT_IN_SHORTLIST", False)
        assert step["capability_ref"] == "sha256:" + digest(supplied) and json.loads(text)["status"] == "DENIED"
        assert len(reads) == before, supplied                 # no registry read for the refused step
    # A caller the AuthorizationPort denies: the refused search step reads nothing.
    from quati.application.discovery import PortResult
    turn.service.authorize = lambda context, operation, action="read": PortResult(
        "DENIED", "FORBIDDEN", "NO_SPACE_GRANT", {"reason": "NO_SPACE_GRANT"}, trace={"handler_executed": False})
    before = len(reads)
    _text, step = execute_tool_call(turn, turn.context, ToolCall("quati_search", {"query": "search my email"}))
    assert (step["status"], step["reason"], step["capability_ref"]) == ("DENIED", "NO_SPACE_GRANT", None)
    assert len(reads) == before


# ----------------------------------------------------------------- P10b: a writer leaves mode 0700 exactly
def test_p10b_a_writer_leaves_a_state_directory_with_mode_0700_exactly(tmp_path):
    """M01 "Data directory" rule 1: the mode of a state directory is 0700. A writer removes every bit beyond
    it, the sticky bit included (not only group and other permission bits); a reader changes nothing."""
    import stat
    data = tmp_path / "data"
    private_fs.state_directory("receipts", root=data)
    receipts = data / "receipts"
    for wider in (0o1700, 0o750, 0o707, 0o1777):
        receipts.chmod(wider)
        assert stat.S_IMODE(receipts.stat().st_mode) == wider
        private_fs.state_directory("receipts", root=data, create=False)
        assert stat.S_IMODE(receipts.stat().st_mode) == 0o700, oct(wider)
    receipts.chmod(0o1700)                                    # a reader: no group or other bit, nothing is changed
    assert private_fs.state_directory("receipts", root=data, create=False, tighten=False) == receipts
    assert stat.S_IMODE(receipts.stat().st_mode) == 0o1700
