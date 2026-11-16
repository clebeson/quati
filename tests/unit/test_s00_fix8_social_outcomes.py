"""S00 fix round 8: third independent audit (docs/audit/S00_AUDIT3_2026-11-16.md), findings X4 and X5.

Binding dispositions discriminated here (docs/governance/LOG.md, LOG-0044):

* X4 (SOC-01; S00-GATE-03 first half; S00_RUNTIME_CONTRACT "Displayed text and social outcomes"
  rule 2): a text that carries a request never matches the code-owned social table.
  (1) demonstratives, pronouns and copulas are not free-standing markers; they exist only inside
  fixed, fully enumerated phrases; (2) no table entry is an ordinary imperative or work word of
  another table language (Italian ``salve`` is Portuguese "save"); (3) after normalization every
  character that is not a letter, mark, number, whitespace, listed punctuation or an allowlisted
  emoji makes the text not social, a punctuation run is short and at most one run between two
  words is free (not attached to a word); (4) a social-only text is short (a bound in words and in
  characters).
* X5 / D7 (M15 no-capability rule; contract rule 4): ``NO_CAPABILITY`` is not a success. It keeps
  ``result_kind = NO_CAPABILITY`` and is UNAVAILABLE / ``UNSUPPORTED``, exit 4, with
  ``work_performed`` false. ``FIXTURE_RESULT`` stays SUCCEEDED only after a validated execution.

Proof tiers. The table tests are L1 (pure domain function). The outcome tests observe the public
path in real child processes: ``python -m quati`` (L2, no provider) or the public ``main`` with
the SCRIPTED FAKE model of ``s00_fix8_runner.py`` (L1; the scripted model is the adversary and is
never evidence of a real provider). No network, no ``QUATI_ALLOW_LIVE``.
"""

from __future__ import annotations

import runpy
import string
import sys
import unicodedata
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from s00_fix8_support import (  # noqa: E402
    CAPABILITY, CLAIM, READ, REPOSITORY_ROOT, new_profile, receipt, social_data, stable, steps)

from quati.domain import social  # noqa: E402

AUDIT_TEXTS = REPOSITORY_ROOT / "evidence/S00/GATES-AUDIT3-2026-11-16/audit-scripts/d1_texts.py"

# ----------------------------------------------------------------- the rule, restated as the oracle
# Integration step 8 (owner decision 2026-11-16: English and Portuguese only). Was: four marker words (with
# "dringend"), ten urgency phrases (with the French, German and Italian ones) and fourteen languages.
MARKER_WORDS = {"urgent", "urgently", "urgente"}
URGENCY_PHRASES = {"this is urgent", "it is urgent", "isto é urgente", "isso é urgente", "é urgente"}
REMOVED_URGENCY = ("dringend", "c'est urgent", "das ist dringend", "es ist dringend", "è urgente", "questo è urgente")
# Demonstratives, pronouns and copulas of the table's languages: never a marker, never a one-word entry.
NOT_FREE_STANDING = ("this that these those it is are am be isto isso este esse esta essa aquilo é e está esto eso "
                     "este es c ce ça est das dies es ist sind è questo quello you do que qué was what").split()
# Ordinary imperative or work words of a table language that an entry of another language could collide with.
WORK_WORDS = ("salve salva salvar save guarda guardar envia envie send delete apaga apague borra supprime "
              "mach tag comment come va esta como que do").split()
PUNCTUATION = set(string.punctuation) | set("¡¿«»‘’‚“”„‹›‐–—―·、。「」『』・،؛؟।")
EMOJI = set("👋🙂😀😃😄😁😊😉☺🙏❤")
MAX_WORDS, MAX_CHARACTERS, MAX_PUNCTUATION_RUN, MAX_FREE_RUNS = 12, 120, 3, 1
LANGUAGES = ("en", "pt")
# Work fragments per language (the two table languages and the twelve removed ones): an instruction, a
# question or a bare demonstrative.
WORK_FRAGMENTS = {
    "en": ["delete everything", "save this", "wire $500", "do this", "send it now", "is it urgent", "this", "it",
           "please forward the contract"],
    "pt": ["apague tudo", "salve isto", "salve isso", "salve", "envie agora", "é isso", "isto", "isso"],
    "es": ["envíalo ahora", "borra todo", "esto es urgente", "qué es esto", "esto"],
    "fr": ["supprime tout", "envoie le maintenant", "c'est quoi"],
    "de": ["mach das", "lösche alles", "das ist es", "das"],
    "it": ["cancella tutto", "salva questo", "questo"],
    "nl": ["verwijder alles", "stuur het nu"],
    "tr": ["hepsini sil", "şimdi gönder"],
    "ru": ["удали всё", "отправь сейчас"],
    "ja": ["削除して", "全部消して"],
    "zh": ["删除所有日历", "发送邮件"],
    "ko": ["모두 삭제해", "지금 보내"],
    "hi": ["सब हटाओ", "abhi bhejo"],
    "ar": ["احذف كل شيء", "أرسل الآن"],
}


def table_phrases(language: str | None = None) -> list[str]:
    return [phrase for code, _template, kinds in social.SOCIAL_TABLE if language in (None, code)
            for listed in kinds.values() for phrase in listed]


def is_social(text: str) -> bool:
    return social.social_match(text) is not None


# ----------------------------------------------------------------- X4: the exact rule is pinned (L1)
def test_x4_rule_constants_are_exactly_the_contract():
    assert tuple(code for code, _template, _kinds in social.SOCIAL_TABLE) == LANGUAGES
    assert set(social.MARKERS) == MARKER_WORDS
    assert set(social.URGENCY_PHRASES) == URGENCY_PHRASES
    assert set(social.PUNCTUATION) == PUNCTUATION
    assert set(social.EMOJI) == EMOJI
    assert (social.MAX_SOCIAL_WORDS, social.MAX_SOCIAL_CHARACTERS, social.MAX_PUNCTUATION_RUN,
            social.MAX_FREE_PUNCTUATION_RUNS) == (MAX_WORDS, MAX_CHARACTERS, MAX_PUNCTUATION_RUN, MAX_FREE_RUNS)
    assert set(social.SKIN_TONES) == {chr(code) for code in range(0x1F3FB, 0x1F400)}
    # Every listed punctuation character and emoji survives normalization unchanged (the rule is applied after it).
    assert all(social.fold(character) == character for character in PUNCTUATION | EMOJI)


def test_x4_clause_1_no_demonstrative_pronoun_or_copula_stands_alone():
    """Such a word may only be part of a fixed phrase of two or more words."""
    single = {phrase[0] for phrase in social.PHRASES if len(phrase) == 1} | set(social.MARKERS)
    assert not single & {social.fold(word) for word in NOT_FREE_STANDING}
    for word in NOT_FREE_STANDING:
        for greeting in ("hello", "olá", "hola", "hallo", "ciao", "bonjour"):
            assert not is_social(f"{greeting}, {word}"), (greeting, word)
            assert not is_social(f"{word} {greeting}"), (greeting, word)
            assert not is_social(f"{greeting}, {word} urgent"), (greeting, word)
    # An urgency phrase is matched whole: its words in another order, or part of it, are not a phrase.
    for text in ("hello, is this urgent", "hello, urgent is this", "hello, this urgent", "hello, is urgent",
                 "olá, é isto urgente", "olá, isto urgente", "hallo, ist das dringend", "hallo, das dringend",
                 "bonjour, est urgent", "ciao, questo urgente"):
        assert not is_social(text), text
    # No politeness, assent or time word is a marker (the marker set is closed).
    for text in ("hello, please", "please, hello", "olá, por favor", "hallo, bitte", "hello, now", "hello, ok",
                 "hello, yes", "olá, sim", "thanks, go ahead"):
        assert not is_social(text), text
    # Urgency alone (markers and urgency phrases, with no greeting, pleasantry or thanks) is not social.
    for text in [*MARKER_WORDS, *URGENCY_PHRASES, "urgent, this is urgent", "urgente, é urgente"]:
        assert not is_social(text), text
    # A marker or urgency phrase of a removed language is an ordinary word next to a greeting.
    for urgency in REMOVED_URGENCY:
        for text in (f"hello, {urgency}", f"{urgency}, hello", f"olá, {urgency}"):
            assert not is_social(text), text


def test_x4_clause_2_no_entry_is_a_work_word_of_another_table_language():
    single = {phrase[0] for phrase in social.PHRASES if len(phrase) == 1} | set(social.MARKERS)
    assert not single & set(WORK_WORDS)
    assert "salve" not in table_phrases()                    # removed: Portuguese imperative "save"
    for text in ("salve", "Salve!", "Salve isto, é urgente", "salve isso", "ciao, salve", "salve, obrigado"):
        assert not is_social(text), text
    # Integration step 8 (owner decision 2026-11-16: English and Portuguese only). Was: `is_social("Ciao!") and
    # is_social("Buongiorno, come stai?")` ("Italian is still covered").
    assert not is_social("Ciao!") and not is_social("Buongiorno, come stai?")


@pytest.mark.parametrize("language", LANGUAGES)
def test_x4_every_table_phrase_alone_and_with_markers_is_social(language):
    owner = {}
    for code, _template, kinds in social.SOCIAL_TABLE:
        for listed in kinds.values():
            for phrase in listed:
                owner.setdefault(social.words(phrase), code)
    phrases = table_phrases(language)
    assert phrases
    for phrase in phrases:
        alone = social.social_match(phrase)
        assert alone is not None and alone.language == owner[social.words(phrase)], phrase
        for variant in (phrase.upper(), f"{phrase}!", f"  {phrase}?  ", f"«{phrase}»", f"{phrase}...", f"{phrase} 😊"):
            found = social.social_match(variant)
            assert found is not None and found.reply == alone.reply, variant
        for marker in sorted(MARKER_WORDS | URGENCY_PHRASES):
            for text in (f"{phrase}, {marker}", f"{marker}: {phrase}", f"{phrase} {marker}", f"{phrase} — {marker}!"):
                found = social.social_match(text)
                assert found is not None and found.reply == alone.reply, text


@pytest.mark.parametrize("language", LANGUAGES)
def test_x4_every_table_phrase_with_a_work_fragment_is_not_social(language):
    """For EVERY table phrase: the phrase followed or preceded by each work fragment of each language."""
    fragments = [fragment for listed in WORK_FRAGMENTS.values() for fragment in listed]
    # Integration step 8: was `set(WORK_FRAGMENTS) == set(LANGUAGES)`; the fragments of the twelve removed
    # languages are kept as work text although their languages left the table.
    assert set(LANGUAGES) < set(WORK_FRAGMENTS) and len(WORK_FRAGMENTS) == 14
    for phrase in table_phrases(language):
        for fragment in fragments:
            for text in (f"{phrase} {fragment}", f"{phrase}, {fragment}", f"{phrase}\n{fragment}", f"{phrase}! {fragment}?",
                         f"{fragment} {phrase}", f"{fragment}, {phrase}", f"{phrase}{fragment}", f"{fragment}{phrase}",
                         f"{phrase}, urgent, {fragment}", f"{phrase} 😊 {fragment}"):
                assert not is_social(text), text


# ----------------------------------------------------------------- X4: every audit text (L1)
# The audit expected these four to be social. The binding character rule (clause 3: a format or tag character
# is never silently dropped) and the length bound (clause 4) make them not social: they go to the model path.
AUDIT_SOCIAL_NOW_NOT_SOCIAL = {"hello " * 5000: "clause 4, length bound", "hello\u200b": "clause 3, U+200B (Cf)",
                               "\u202ehello": "clause 3, U+202E (Cf)",
                               "hello\U000E0064\U000E0065\U000E006C": "clause 3, tag characters (Cf)",
                               # Integration step 8: five more of the audit's "S" texts, in removed languages.
                               "İyi günler": "owner decision 2026-11-16: English and Portuguese only",
                               "MERHABA": "owner decision 2026-11-16: English and Portuguese only",
                               "こんにちは": "owner decision 2026-11-16: English and Portuguese only",
                               "你好": "owner decision 2026-11-16: English and Portuguese only",
                               "Привет, как дела?": "owner decision 2026-11-16: English and Portuguese only"}


def test_x4_every_audit_text_behaves_as_the_audit_requires():
    texts = runpy.run_path(str(AUDIT_TEXTS))["T"]
    assert len(texts) == 74 and {expectation for _text, expectation in texts} == {"S", "W"}
    overridden = set()
    for text, expectation in texts:
        if text in AUDIT_SOCIAL_NOW_NOT_SOCIAL:
            assert expectation == "S"
            overridden.add(text)
            expectation = "W"
        assert is_social(text) == (expectation == "S"), ascii(text[:80])
    assert overridden == set(AUDIT_SOCIAL_NOW_NOT_SOCIAL)
    # The opposite direction found by the audit (P3) and the coordinator's examples.
    assert social.social_match("hello ❤\ufe0f").reply == "Hello!"
    assert social.social_match("bom dia 😊").reply == "Olá!"
    # The audit's X4 table, verbatim.
    for text in ("Salve isto, é urgente", "salve isso", "How do you do this?", "how do you do it",
                 "hello 🅳🅴🅻🅴🆃🅴 🅰🅻🅻 🅴🆅🅴🅽🆃🆂", "hi 🇩 🇪 🇱 🇪 🇹 🇪", "hello -.. . .-.. . - . / .- .-.. .-..",
                 "hello ⠙⠑⠇⠑⠞⠑ ⠁⠇⠇", "hi, is it urgent?", "como está isto?", "e aí, é isso?"):
        assert not is_social(text), text
    assert is_social("How do you do?") and is_social("Hello, how do you do?")       # the complete fixed phrase


# ----------------------------------------------------------------- X4 clause 3: Unicode bypass classes (L1)
BYPASS_CLASSES = {
    "negative_squared_latin": "hello 🅳🅴🅻🅴🆃🅴 🅰🅻🅻",
    "squared_latin": "hello 🄳🄴🄻🄴🅃🄴",
    "negative_circled_latin": "hello 🅓🅔🅛🅔🅣🅔",
    "circled_latin_becomes_a_word": "hello ⒹⒺⓁⒺⓉⒺ",
    "parenthesized_latin_becomes_words": "hello ⒟⒠⒧⒠⒯⒠",
    "regional_indicators": "hi 🇩 🇪 🇱 🇪 🇹 🇪",
    "regional_indicator_pair": "hello 🇩🇪",
    "braille": "hello ⠙⠑⠇⠑⠞⠑ ⠁⠇⠇",
    "morse_spaced": "hello -.. . .-.. . - . / .- .-.. .-..",
    "morse_one_run": "hello -...-.-..-",
    "morse_middle_dots": "hello ·−· −−",
    "mathematical_bold_becomes_a_word": "hello 𝐝𝐞𝐥𝐞𝐭𝐞 𝐚𝐥𝐥",
    "mathematical_double_struck_becomes_a_word": "hello 𝕕𝕖𝕝𝕖𝕥𝕖",
    "fullwidth_becomes_a_word": "hello ｄｅｌｅｔｅ",
    "superscript_becomes_a_word": "hello ᵈᵉˡᵉᵗᵉ",
    "small_capitals": "hi ᴅᴇʟᴇᴛᴇ ᴀʟʟ",
    "tag_characters": "hello\U000E0064\U000E0065\U000E006C\U000E0065\U000E0074\U000E0065",
    "tag_characters_after_an_emoji": "hello 😊\U000E0064\U000E0065\U000E006C",
    "private_use_bmp": "hello \ue000\ue001",
    "private_use_plane_15": "hello \U000F0000",
    "unassigned": "hello \u0378",
    "noncharacter": "hello \uffff",
    "lone_surrogate": "hello \ud800",
    "zero_width_space": "hello\u200b",
    "zero_width_non_joiner": "hel\u200clo",
    "zero_width_joiner_between_letters": "hel\u200dlo",
    "word_joiner": "hello\u2060",
    "byte_order_mark": "\ufeffhello",
    "soft_hyphen": "hel\u00adlo",
    "right_to_left_override": "\u202ehello",
    "isolate": "\u2066hello\u2069",
    "escape_sequence": "hello\x1b[2J",
    "nul": "hello\x00",
    "bell": "hello\x07",
    "vertical_tab": "hello\x0bhi",
    "line_separator": "hello\u2028hi",
    "paragraph_separator": "hello\u2029hi",
    "arrow": "hello → hi",
    "math_operator": "hello ∑",
    "fraction_slash_from_normalization": "hello ½",
    "currency_sign": "hello €",
    "box_drawing": "hello ─",
    "dingbat": "hello ✂",
    "pictograph_outside_the_allowlist": "hello 📧",
    "pictographs_spelling_an_action": "hi ➡\ufe0f 📧 👔 💰",
    "thumbs_up_is_not_allowlisted": "thanks 👍",
    "keycap_sequence": "hi 1\ufe0f\u20e3",
    "variation_selector_without_an_emoji": "hello\ufe0f",
    "variation_selector_after_punctuation": "hello!\ufe0f",
    "skin_tone_without_an_emoji": "hello \U0001f3fd",
    "second_skin_tone": "hello 👋\U0001f3fd\U0001f3fd",
    "zero_width_joiner_after_an_emoji": "hello 😊\u200d",
    "zero_width_joiner_to_an_unlisted_emoji": "hello ❤\ufe0f\u200d🔥",
    "punctuation_outside_the_set": "hello •",
    "section_sign": "hello §",
    "dagger": "hello †",
    "interrobang": "hello ‽",
    "homoglyph_word": "hello dеlеtе all",
    "combining_strikethrough": "hello d\u0336e\u0336l\u0336e\u0336t\u0336e\u0336",
    "enclosing_mark": "hello\u20dd",
    "percent_encoding": "hello %64%65%6c%65%74%65",
    "digits": "hello 500",
}


@pytest.mark.parametrize("name", sorted(BYPASS_CLASSES))
def test_x4_clause_3_no_character_class_is_silently_dropped(name):
    text = BYPASS_CLASSES[name]
    assert is_social("hello")                                # control: only the extra characters decide
    assert not is_social(text), ascii(text)


def test_x4_clause_3_every_code_point_outside_the_rule_makes_a_greeting_not_social():
    """Exhaustive over the Basic Multilingual Plane and the planes that hold the audit's characters: a
    character is accepted next to a greeting only if the rule names its class."""
    accepted_elsewhere = EMOJI | {"\ufe0f"} | {chr(code) for code in range(0x1F3FB, 0x1F400)}
    ranges = [range(0x0, 0x3000), range(0xE000, 0xE100), range(0xFE00, 0x10000), range(0x1D400, 0x1D800),
              range(0x1F100, 0x1F700), range(0xE0000, 0xE0080), range(0xF0000, 0xF0010)]
    for code in (code for block in ranges for code in block):
        character = chr(code)
        folded = social.fold(character)
        named = all(unicodedata.category(item)[0] in "LMN" or unicodedata.category(item) == "Zs"
                    or item in "\t\n\r" or item in PUNCTUATION or item in accepted_elsewhere for item in folded)
        if not named:
            assert not is_social(f"hello {character}"), hex(code)
            assert not is_social(f"{character} hello"), hex(code)
            assert not is_social(f"good {character} morning"), hex(code)


@pytest.mark.parametrize("text, reply", [
    ("hello ❤\ufe0f", "Hello!"), ("hello ❤", "Hello!"), ("bom dia 😊", "Olá!"), ("hello 👋", "Hello!"),
    ("👋 hello", "Hello!"), ("hello 👋\U0001f3fd", "Hello!"), ("thanks 🙏\U0001f3ff", "Hello!"), ("hi 😊😊", "Hello!"),
    ("hi 😊 👋 ❤\ufe0f!", "Hello!"), ("good 😀 morning", "Hello!"), ("Olá 🙂, tudo bem? 😉", "Olá!"),
    # Integration step 8 (owner decision 2026-11-16: English and Portuguese only). Were: ("hallo ☺\ufe0f", "Hallo!")
    # and ("merci 😄😁😃", "Bonjour!"); the same emoji now follow Portuguese entries.
    ("olá ☺\ufe0f", "Olá!"), ("obrigado 😄😁😃", "Olá!"), ("hello ❤\ufe0f\u200d😊", "Hello!"),
    ("hello 👋\U0001f3fd\u200d❤", "Hello!"),
])
def test_x4_clause_3_allowlisted_emoji_keep_a_greeting_social(text, reply):
    assert social.social_match(text).reply == reply


def test_x4_clause_3_an_allowlisted_emoji_does_not_make_a_removed_language_social():
    for text in ("hallo ☺\ufe0f", "merci 😄😁😃", "hola 👋", "ciao 😊"):
        assert not is_social(text), text


def test_x4_clause_3_an_emoji_is_never_a_phrase():
    for text in ("👋", "😊😊", "❤\ufe0f", "🙏 urgent", "👋!"):
        assert not is_social(text), text


@pytest.mark.parametrize("text, expected", [
    ("HELLO!!!", True), ("hello!!!!", False), ("hello?!", True), ("hello...", True), ("hello…", True),
    ("hello....", False), ("hello‼", True), ("hello‼‼", False), ('"hello"', True), ("¡Olá!", True),
    ("¿Tudo bem?", True), ("hello - hi", True), ("hi — urgent: hi", True), ("hello , . hi", False),
    ("hello . . .", False), ("hello ! ?", False), ("! ? hello", False), ("hello -..", True), ("hello -.. .", False),
    ("hello:-)", True), ("hello :-) !", False), ("olá。", True), ("oi！", True), ("olá、obrigado。", True),
    ("¡Olá! ¿Tudo bem?", True), ("Bom dia, ¿tudo bem?", True), ('"Hello." "Hi."', True),
    ("Hello! — ¿Tudo bem?", True), ("hello. - . hi", False), ("hello. -.. .hi", True), ("hello.... hi", False),
    ("hello — — hi", False), ("-.. hello", True), ("-.. . hello", False), ("hello,hi", True), ("hello!?!hi", True),
    ("hello!?!?hi", False), ("— hello —", True), ("— hello — —", False), ("...", False), ("- . -", False),
    ("olá، obrigado؟", True), ("olá।", True), ("«Bom dia»", True), ("„Olá“", True), ("what's up", True),
    # Integration step 8 (owner decision 2026-11-16: English and Portuguese only). The twelve rows above that held
    # a phrase of a removed language keep their punctuation and now hold a Portuguese phrase; the original texts
    # were True and are False, because of their language and not of their punctuation.
    ("¡Hola!", False), ("¿Qué tal?", False), ("こんにちは。", False), ("你好！", False), ("你好、谢谢。", False),
    ("¡Hola! ¿Qué tal?", False), ("Buenos días, ¿qué tal?", False), ("Hello! — ¿Qué tal?", False),
    ("مرحبا، شكرا؟", False), ("नमस्ते।", False), ("«Bonjour»", False), ("„Hallo“", False),
    ("what’s up", True), ("hello! 😊", True), ("hello 😊!", True), ("hello! 😊 !", True), ("hello 😊! !", False),
    ("hello !😊! hi", False),
])
def test_x4_clause_3_punctuation_runs_are_short_and_at_most_one_is_free(text, expected):
    """A run of listed punctuation has at most three characters (whitespace or an emoji ends it). A run that
    directly follows or precedes a word is attached; before the first word, between two words and after the
    last word at most one run is free. Morse-like sequences are several free runs."""
    assert is_social(text) is expected


def test_x4_clause_3_whitespace_is_space_tab_and_line_break_only():
    for text in ("hello\thi", "hello\nhi", "hello\r\nhi", "hello\u00a0hi", "hello\u3000hi", "hello\u2003hi", " hello "):
        assert is_social(text), ascii(text)


def test_x4_clause_4_length_bound_in_words_and_characters():
    assert is_social(" ".join(["hello"] * MAX_WORDS))
    assert not is_social(" ".join(["hello"] * (MAX_WORDS + 1)))
    assert is_social("hello" + " " * (MAX_CHARACTERS - 5))
    assert not is_social("hello" + " " * (MAX_CHARACTERS - 4))
    assert not is_social("hello " * 5000) and not is_social("hello " * 20000)
    assert not is_social("hello" + "!" * 200) and not is_social("😊" * 200 + "hello")
    # The bound is measured after normalization: U+2026 is one character before it and three after it.
    assert is_social("hello." + " " * (MAX_CHARACTERS - 6))
    assert not is_social("hello\u2026" + " " * (MAX_CHARACTERS - 6))
    assert is_social("Good morning! How are you doing today? Thank you very much!")     # eleven words


def test_x4_reply_selection_is_unchanged():
    # Integration step 8 (owner decision 2026-11-16: English and Portuguese only). Were: "merci" -> "Bonjour!",
    # "das ist dringend, hallo" -> "Hallo!", "es ist dringend. Danke!" -> language "de", "спасибо" -> DEFAULT_REPLY.
    # The same rules are asserted on Portuguese and English text; the old texts are not social.
    assert social.social_match("obrigado").reply == "Olá!"                   # no greeting: the language's template
    assert social.social_match("thanks, bom dia").reply == "Olá!"            # the first greeting decides
    assert social.social_match("isto é urgente, olá").reply == "Olá!"        # an urgency phrase selects no reply
    assert social.social_match("é urgente. Obrigada!").language == "pt"
    assert social.social_match("thanks").reply == social.DEFAULT_REPLY == "Hello!"
    for text in ("merci", "das ist dringend, hallo", "es ist dringend. Danke!", "спасибо"):
        assert social.social_match(text) is None, text
    assert social.words("c'est urgent, नमस्ते") == ("c", "est", "urgent", "नमस्ते")
    assert social.words("hello \U0001F173") is None and social.words("") == ()


# ----------------------------------------------------------------- child processes: ask and chat agree
SOCIAL_SAMPLE = [("hello ❤\ufe0f", "Hello!"), ("bom dia 😊", "Olá!"), ("Olá, isto é urgente", "Olá!"),
                 ("Olá, tudo bem?", "Olá!"), ("How do you do?", "Hello!"), ("thanks 🙏", "Hello!"),
                 ("HELLO!!!", "Hello!"), ("ＨＥＬＬＯ", "Hello!"), ("Boa noite, como vai?", "Olá!")]
# Integration step 8 (owner decision 2026-11-16: English and Portuguese only): ("Hallo, es ist dringend", "Hallo!")
# and ("Ciao, come stai?", "Ciao!") were in SOCIAL_SAMPLE; they are the first two entries of WORK_SAMPLE now.
WORK_SAMPLE = ["Hallo, es ist dringend", "Ciao, come stai?", "Salve isto, é urgente", "salve isso", "How do you do this?", "how do you do it",
               "hello 🅳🅴🅻🅴🆃🅴 🅰🅻🅻 🅴🆅🅴🅽🆃🆂", "hi 🇩 🇪 🇱 🇪 🇹 🇪", "hello -.. . .-.. . - . / .- .-.. .-..",
               "hello ⠙⠑⠇⠑⠞⠑ ⠁⠇⠇", "hi, is it urgent?", "como está isto?", "e aí, é isso?",
               "hello\U000E0064\U000E0065\U000E006C", "hello \ue000", "hello\u200b", "hi ➡\ufe0f 📧 👔 💰",
               " ".join(["hello"] * 13)]
LABELLED_SOCIAL = [["classify_social"], ["final", CLAIM], ["final", CLAIM]]
HOSTILE = [["classify"], *READ]


@pytest.fixture(scope="module")
def probed(tmp_path_factory):
    return new_profile(tmp_path_factory.mktemp("fix8") / "profile")


def test_x4_social_sample_is_answered_identically_by_ask_and_chat_jsonl(probed):
    """A probed model that would label the greeting as work and invoke a capability is never asked."""
    before = len(probed.audit())
    code, turns, _output = probed.chat(HOSTILE, [text for text, _reply in SOCIAL_SAMPLE])
    assert code == 0 and probed.spied("request") == [] and probed.spied("script_left") == [len(HOSTILE)]
    for (text, reply), turn in zip(SOCIAL_SAMPLE, turns):
        code, value, _output = probed.ask(HOSTILE, text)
        assert code == 0 and value["status"] == "SUCCEEDED", text
        assert stable(value)["data"] == social_data(reply) and stable(turn) == stable(value), text
        assert probed.spied("request") == [] and probed.spied("handler") == []
        code, plain, _output = probed.ask(None, text)                 # no provider configured: the same answer
        assert code == 0 and stable(plain) == stable(value), text
    assert probed.audit()[before:] == []


def test_x4_request_bearing_sample_is_never_a_greeting_without_a_provider(probed):
    """L2, the plain product CLI: the audit's texts are refused as work (no provider), one-shot and in chat."""
    code, turns, output = probed.chat(None, WORK_SAMPLE)
    assert code == 0 and "GREETING" not in output
    for text, turn in zip(WORK_SAMPLE, turns):
        code, value, output = probed.ask(None, text)
        assert (code, value["status"], value["error"]["code"]) == (3, "BLOCKED", "NOT_CONFIGURED"), ascii(text)
        assert value["data"]["result_kind"] == "BLOCKED" and "text" not in value["data"]
        assert "Hello!" not in output and "Ciao!" not in output
        assert stable(turn) == stable(value), ascii(text)


def test_x4_request_bearing_sample_reaches_the_model_and_a_social_label_is_blocked(probed):
    """The texts the round 7 table answered "Ciao!" / "Hello!" with exit 0 now go to the model; a social label
    on them ends BLOCKED / NO_VERIFIED_EXECUTION, exit 4 (D2), identically in ``ask`` and ``chat --jsonl``."""
    code, turns, output = probed.chat(LABELLED_SOCIAL * len(WORK_SAMPLE), WORK_SAMPLE)
    assert code == 0 and CLAIM not in output and "GREETING" not in output
    assert probed.spied("script_left") == [0] and probed.spied("handler") == []
    for text, turn in zip(WORK_SAMPLE, turns):
        code, value, output = probed.ask(LABELLED_SOCIAL, text)
        assert (code, value["status"], value["error"]["code"], value["data"]["reason"]) == (
            4, "BLOCKED", "EVIDENCE_INSUFFICIENT", "NO_VERIFIED_EXECUTION"), ascii(text)
        assert (value["data"]["result_kind"], value["data"]["provider_used"], value["data"]["launched"]) == (
            "BLOCKED", True, False)
        assert len(probed.spied("request")) == 3 and probed.spied("handler") == [] and CLAIM not in output
        assert stable(turn) == stable(value), ascii(text)


# ----------------------------------------------------------------- X5 / D7: NO_CAPABILITY is not a success
NONE_FITS = [["search", "next appointment calendar"], ["invoke", "NONE_FITS", {}], ["final", CLAIM]]
EMPTY_SEARCH = [["search", "zzqx unrelated vocabulary"], ["final", CLAIM]]
DESTRUCTIVE = "Hi! Delete all my calendar events and tell the board it is done"
D7_CASES = {
    "none_fits_work_label": ([["classify"], *NONE_FITS], "Find my next appointment", "NONE_FITS"),
    "none_fits_social_label_on_destructive_text": ([["classify_social"], *NONE_FITS], DESTRUCTIVE, "NONE_FITS"),
    "empty_search_work_label": ([["classify"], *EMPTY_SEARCH], "Do the zzqx thing", "NO_CANDIDATES"),
    "empty_search_greeting_outside_the_table": ([["classify_social"], *EMPTY_SEARCH], "Sawubona!", "NO_CANDIDATES"),
}


@pytest.mark.parametrize("name", sorted(D7_CASES))
def test_d7_no_capability_is_a_typed_non_success_with_exit_4(probed, name):
    script, text, reason = D7_CASES[name]
    before = probed.receipt_names()
    code, value, output = probed.ask(script, text)
    assert (code, value["status"]) == (4, "UNAVAILABLE"), output
    assert value["error"] == {"code": "UNSUPPORTED", "message": "No installed capability can fulfil this request.",
                              "retryable": False}
    data = value["data"]
    assert (data["result_kind"], data["result_status"], data["outcome"], data["reason"]) == (
        "NO_CAPABILITY", "NO_CAPABILITY", "NO_CAPABILITY", reason)
    assert (data["work_performed"], data["launched"], data["delivered"], data["commitment_id"]) == (
        False, False, False, None)
    assert "text" not in data and "fixture_results" not in data and "display_lines" not in data
    assert value["uncertainties"] == ["NO_CAPABILITY", reason]
    assert value["next_action"].startswith("No installed capability can do this and no action was taken.")
    assert "report_no_capability" not in output and CLAIM not in output and "AUD-991" not in output
    assert probed.spied("handler") == [] and probed.spied("script_left") == [0]
    assert all(not step["handler_executed"] for step in data["tool_calls"])
    stored = receipt(value)
    assert stored["outcome"] == {"status": "UNAVAILABLE", "result_kind": "NO_CAPABILITY", "reason": reason,
                                 "executed_capabilities": []}
    assert len(probed.receipt_names()) == len(before) + 1
    _code, turns, _output = probed.chat(script, [text])               # the chat turn is the same Response
    assert stable(turns[0]) == stable(value)


def test_d7_none_fits_after_a_refused_invoke_is_still_not_a_success(probed):
    script = [["classify"], ["search", "next appointment calendar"], ["invoke", "fixtures.calendar-write", {}],
              ["invoke", "NONE_FITS", {}], ["final", CLAIM]]
    code, value, _output = probed.ask(script, "Create an event")
    assert (code, value["status"], value["error"]["code"], value["data"]["result_kind"]) == (
        4, "UNAVAILABLE", "UNSUPPORTED", "NO_CAPABILITY")
    assert probed.spied("handler") == []


def test_d7_fixture_result_is_succeeded_only_with_a_validated_execution(probed):
    """Control (unchanged): a handler really executed and its output validated."""
    code, value, _output = probed.ask([["classify"], *READ], "Find my next appointment")
    assert (code, value["status"], value["data"]["result_kind"], value["error"]) == (
        0, "SUCCEEDED", "FIXTURE_RESULT", None)
    assert steps(value)[-1] == ("invoke", "SUCCEEDED", None, True) and probed.spied("handler") == ["calendar-read"]
    assert [item["capability_id"] for item in value["data"]["fixture_results"]] == [CAPABILITY]
    assert receipt(value)["outcome"]["executed_capabilities"] == [f"{CAPABILITY}@1.0.0"]
    # NONE_FITS declared after a validated execution does not undo the validated result.
    code, value, _output = probed.ask([["classify"], *READ[:3], ["invoke", "NONE_FITS", {}], ["final", "x"]],
                                      "Find my next appointment")
    assert (code, value["status"], value["data"]["result_kind"]) == (0, "SUCCEEDED", "FIXTURE_RESULT")


def test_d7_no_work_request_ends_succeeded_without_a_validated_execution(probed):
    """Contract rule 4 over every scripted ending that executes nothing: none is SUCCEEDED or exit 0."""
    endings = [[["final", CLAIM], ["final", CLAIM]], NONE_FITS, EMPTY_SEARCH,
               [["search", "next appointment calendar"], ["final", CLAIM], ["final", CLAIM]],
               [["search", "next appointment calendar"], ["describe", CAPABILITY], ["final", CLAIM], ["final", CLAIM]],
               [["invoke", CAPABILITY, {"limit": 1}], ["final", CLAIM]], []]
    for label in ("classify", "classify_social"):
        for ending in endings:
            for text in (DESTRUCTIVE, "Moikka!"):
                code, value, output = probed.ask([[label], *ending], text)
                assert code != 0 and value["status"] not in ("SUCCEEDED", "PARTIAL"), (label, ending, text)
                assert value["data"]["launched"] is False and probed.spied("handler") == []
                assert CLAIM not in output
