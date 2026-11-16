"""Code-owned multilingual social table (S00_RUNTIME_CONTRACT "Displayed text and social outcomes").

A text is *social-only* when all of the following hold (LOG-0041 D1, LOG-0044 X4):

1. *Characters.* After ``fold`` (Unicode NFKC and casefold) every character is a letter, a combining
   mark or a number (general category L, M, N: a word character), whitespace (category Zs, tab, line
   feed, carriage return), a character of ``PUNCTUATION`` or part of an emoji of ``EMOJI``. An emoji
   may be followed by U+FE0F or one skin-tone modifier, and U+200D may join two such emoji. Any other
   character (symbols, enclosed or regional-indicator letters, Braille, format and tag characters,
   controls, private-use and unassigned code points) makes the text not social: nothing is dropped.
2. *Punctuation.* A run of punctuation (whitespace or an emoji ends it) has at most
   ``MAX_PUNCTUATION_RUN`` characters. A run that directly follows or directly precedes a word is
   attached to it; any other run is free. Before the first word, between two words and after the last
   word there is at most one free run. A sequence of punctuation groups (Morse-like text) is
   therefore not social, while "¡Hola! ¿Qué tal?" is.
3. *Length.* The folded text has at most ``MAX_SOCIAL_CHARACTERS`` characters and
   ``MAX_SOCIAL_WORDS`` words.
4. *Phrases.* Its words, in order, can be cut completely into phrases of ``SOCIAL_TABLE`` (greetings,
   pleasantries, thanks), phrases of ``URGENCY_PHRASES`` and single ``MARKERS`` words, with at least
   one table phrase. Matching is on whole phrases, never on a bag of words.

Such a text asks for nothing: the application answers it with its own deterministic template and no
model is called. Every other text is outside the table.

The table is data. Demonstratives, pronouns and copulas ("this", "it", "is", "isto", "é", "das",
"ist") are never markers and never one-word entries: they occur only inside the fixed phrases listed
here ("this is urgent", "how are you"), so "how do you do this" or "salve isto" is not social. No
entry is an ordinary imperative or work word of another table language. Unaccented spellings are
listed explicitly; nothing is stripped from the input.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

DEFAULT_REPLY = "Hello!"       # the reply of a language that has no template of its own
GREETING, PLEASANTRY, THANKS = "greeting", "pleasantry", "thanks"

# (language, reply template or None, {kind: phrases}). A language's template answers its phrases;
# None falls back to DEFAULT_REPLY (English). A phrase belongs to the first language that lists it.
SOCIAL_TABLE: tuple[tuple[str, str | None, dict[str, tuple[str, ...]]], ...] = (
    ("en", "Hello!", {
        GREETING: ("hello", "hi", "hey", "hello there", "hi there", "hey there", "good morning", "good afternoon",
                   "good evening", "good day", "howdy", "hiya", "greetings", "yo"),
        PLEASANTRY: ("how are you", "how are you doing", "how are you today", "how are you doing today",
                     "how is it going", "how's it going", "how do you do", "what's up", "whats up"),
        THANKS: ("thanks", "thank you", "thanks a lot", "many thanks", "thank you very much"),
    }),
    ("pt", "Olá!", {
        GREETING: ("olá", "ola", "oi", "bom dia", "boa tarde", "boa noite"),
        PLEASANTRY: ("tudo bem", "tudo bom", "tudo bem com você", "tudo bem com voce", "como vai", "como vai você", "como vai voce", "como você está",
                     "como voce esta", "como está", "e você", "e voce", "e aí", "e ai"),
        THANKS: ("obrigado", "obrigada", "muito obrigado", "muito obrigada", "valeu"),
    }),
    ("es", "¡Hola!", {
        GREETING: ("hola", "buenos días", "buenos dias", "buenas tardes", "buenas noches", "buenas"),
        PLEASANTRY: ("qué tal", "que tal", "cómo estás", "como estas", "cómo está usted", "como esta usted"),
        THANKS: ("gracias", "muchas gracias"),
    }),
    ("fr", "Bonjour!", {
        GREETING: ("bonjour", "bonsoir", "salut", "coucou"),
        PLEASANTRY: ("ça va", "ca va", "comment ça va", "comment ca va", "comment allez vous", "comment vas tu"),
        THANKS: ("merci", "merci beaucoup"),
    }),
    ("de", "Hallo!", {
        GREETING: ("hallo", "guten tag", "guten morgen", "guten abend", "moin", "moin moin", "servus",
                   "grüß gott", "grüss gott", "gruss gott"),
        PLEASANTRY: ("wie geht es dir", "wie geht es ihnen", "wie geht's", "wie gehts", "alles gut", "alles klar"),
        THANKS: ("danke", "danke schön", "danke schon", "vielen dank"),
    }),
    ("it", "Ciao!", {
        GREETING: ("ciao", "buongiorno", "buonasera"),
        PLEASANTRY: ("come stai", "come sta", "come va", "tutto bene"),
        THANKS: ("grazie", "grazie mille"),
    }),
    ("nl", None, {
        GREETING: ("hoi", "goedemorgen", "goedemiddag", "goedenavond", "goedendag"),
        PLEASANTRY: ("hoe gaat het", "hoe gaat het met je", "hoe gaat het met u"),
        THANKS: ("bedankt", "dank je", "dank je wel", "dank u"),
    }),
    ("tr", None, {
        GREETING: ("merhaba", "selam", "günaydın", "günaydin", "gunaydin", "iyi günler", "iyi gunler", "iyi akşamlar",
                   "iyi aksamlar"),
        PLEASANTRY: ("nasılsın", "nasilsin", "nasılsınız", "nasilsiniz"),
        THANKS: ("teşekkürler", "tesekkurler", "teşekkür ederim", "tesekkur ederim"),
    }),
    ("ru", None, {
        GREETING: ("привет", "здравствуйте", "здравствуй", "добрый день", "доброе утро", "добрый вечер"),
        PLEASANTRY: ("как дела", "как ты", "как вы"),
        THANKS: ("спасибо", "спасибо большое", "большое спасибо"),
    }),
    ("ja", None, {
        GREETING: ("こんにちは", "おはよう", "おはようございます", "こんばんは", "konnichiwa"),
        PLEASANTRY: ("お元気ですか", "元気ですか"),
        THANKS: ("ありがとう", "ありがとうございます"),
    }),
    ("zh", None, {
        GREETING: ("你好", "您好", "大家好", "早上好", "晚上好", "ni hao"),
        PLEASANTRY: ("你好吗", "您好吗"),
        THANKS: ("谢谢", "謝謝"),
    }),
    ("ko", None, {
        GREETING: ("안녕하세요", "안녕", "안녕하십니까"),
        PLEASANTRY: ("잘 지내세요", "잘 지냈어요"),
        THANKS: ("감사합니다", "고맙습니다"),
    }),
    ("hi", None, {
        GREETING: ("नमस्ते", "नमस्कार", "namaste", "namaskar"),
        PLEASANTRY: ("आप कैसे हैं", "कैसे हो"),
        THANKS: ("धन्यवाद", "शुक्रिया"),
    }),
    ("ar", None, {
        GREETING: ("مرحبا", "مرحباً", "السلام عليكم", "أهلا", "اهلا", "صباح الخير", "مساء الخير"),
        PLEASANTRY: ("كيف حالك",),
        THANKS: ("شكرا", "شكراً"),
    }),
)
# A greeting whose own template differs from its language's template.
GREETING_REPLIES = {"bonsoir": "Bonsoir!", "salut": "Salut!", "buongiorno": "Buongiorno!"}
# Urgency. A marker word names no object and no action. The demonstrative or copula that carries it exists
# only inside these fixed phrases. Urgency alone is not social (SOC-01 negative: "urgent" needs a greeting).
MARKERS = frozenset(("urgent", "urgently", "urgente", "dringend"))
URGENCY_PHRASES = ("this is urgent", "it is urgent", "isto é urgente", "isso é urgente", "é urgente", "c'est urgent",
                   "das ist dringend", "es ist dringend", "è urgente", "questo è urgente")
# Ordinary punctuation: ASCII punctuation and the sentence punctuation, quotes and dashes of the table's scripts.
PUNCTUATION = frozenset("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~" "¡¿«»‘’‚“”„‹›‐–—―·" "、。「」『』・" "،؛؟" "।")
# Pictographic emoji that name no object and no action (a smile, a wave, folded hands, a heart).
EMOJI = frozenset("\U0001F44B\U0001F642\U0001F600\U0001F603\U0001F604\U0001F601\U0001F60A\U0001F609\u263A"
                  "\U0001F64F\u2764")
VARIATION_SELECTOR, ZERO_WIDTH_JOINER = "\uFE0F", "\u200D"       # allowed only as part of an emoji of EMOJI
SKIN_TONES = frozenset(chr(code) for code in range(0x1F3FB, 0x1F400))
WHITESPACE = "\t\n\r"                                            # besides general category Zs
MAX_SOCIAL_WORDS = 12
MAX_SOCIAL_CHARACTERS = 120
MAX_PUNCTUATION_RUN = 3
MAX_FREE_PUNCTUATION_RUNS = 1


@dataclass(frozen=True)
class SocialMatch:
    """The deterministic answer to a social-only text."""

    language: str      # the language of the phrase that selected the reply
    reply: str         # application-owned template


def fold(text: str) -> str:
    """Unicode NFKC and casefold; the casefold of the Turkish dotted capital I is a plain ``i``."""
    folded = unicodedata.normalize("NFKC", unicodedata.normalize("NFKC", text).casefold())
    return folded.replace("i̇", "i")


def _emoji_end(text: str, index: int) -> int:
    """The index after the emoji that starts at ``index``: the emoji, an optional U+FE0F or skin-tone
    modifier, and any further emoji of ``EMOJI`` joined to it by U+200D."""
    index += 1
    while True:
        if index < len(text) and (text[index] == VARIATION_SELECTOR or text[index] in SKIN_TONES):
            index += 1
        if index + 1 < len(text) and text[index] == ZERO_WIDTH_JOINER and text[index + 1] in EMOJI:
            index += 2
            continue
        return index


def _gap_allowed(gap: str, after_word: bool, before_word: bool) -> bool:
    """The punctuation rule for one gap (the text before the first word, between two words or after the
    last word). ``gap`` holds ``p`` per punctuation character and a space per whitespace or emoji."""
    runs = gap.split()
    attached = int(after_word and gap.startswith("p")) + int(before_word and gap.endswith("p"))
    return (all(len(run) <= MAX_PUNCTUATION_RUN for run in runs)
            and len(runs) - min(attached, len(runs)) <= MAX_FREE_PUNCTUATION_RUNS)


def words(text: str) -> tuple[str, ...] | None:
    """The words of the folded text (runs of letters, combining marks and numbers), or None when the text
    breaks the character, punctuation or length rule of the module docstring."""
    folded = fold(text)
    if len(folded) > MAX_SOCIAL_CHARACTERS:
        return None
    found: list[str] = []
    current: list[str] = []
    gap: list[str] = []            # the gap since the last word: "p" for punctuation, " " for whitespace or emoji
    index = 0
    while index < len(folded):
        character = folded[index]
        if unicodedata.category(character)[0] in "LMN":
            if not current and not _gap_allowed("".join(gap), bool(found), True):
                return None
            current.append(character)
            gap = []
            index += 1
            continue
        if current:
            found.append("".join(current))
            current = []
        if character in EMOJI:
            index = _emoji_end(folded, index)
            gap.append(" ")
            continue
        index += 1
        if character in WHITESPACE or unicodedata.category(character) == "Zs":
            gap.append(" ")
        elif character in PUNCTUATION:
            gap.append("p")
        else:
            return None            # a character the rule does not name is never silently dropped
    if current:
        found.append("".join(current))
    if not _gap_allowed("".join(gap), bool(found), False) or len(found) > MAX_SOCIAL_WORDS:
        return None
    return tuple(found)


def _compile() -> dict[tuple[str, ...], tuple[str, str, str]]:
    """phrase words -> (language, kind, reply); the first language that lists a phrase keeps it."""
    phrases: dict[tuple[str, ...], tuple[str, str, str]] = {}
    for language, template, kinds in SOCIAL_TABLE:
        for kind, listed in kinds.items():
            for phrase in listed:
                reply = GREETING_REPLIES.get(phrase, template or DEFAULT_REPLY)
                phrases.setdefault(words(phrase), (language, kind, reply))
    return phrases


PHRASES = _compile()
URGENCY = frozenset(words(phrase) for phrase in URGENCY_PHRASES) | frozenset((marker,) for marker in MARKERS)
MAX_PHRASE_WORDS = max(len(phrase) for phrase in (*PHRASES, *URGENCY))


def social_match(text: str) -> SocialMatch | None:
    """The reply to a social-only text, or None for any other text.

    The reply is the template of the first greeting in the text; a text without a greeting
    (thanks, pleasantries) gets the template of its first phrase's language."""
    tokens = words(text)
    if not tokens:
        return None                                     # no word, or a character or length rule is broken
    count = len(tokens)
    # step[i]: words of the longest table or urgency phrase at i from which the rest of the text can
    # still be cut; 0 when the text cannot be cut from i. Filled from the end.
    step = [0] * count + [1]
    for index in range(count - 1, -1, -1):
        for size in range(min(MAX_PHRASE_WORDS, count - index), 0, -1):
            piece = tokens[index:index + size]
            if (piece in PHRASES or piece in URGENCY) and step[index + size]:
                step[index] = size
                break
    if not step[0]:
        return None
    found, index = [], 0
    while index < count:
        entry = PHRASES.get(tokens[index:index + step[index]])
        if entry is not None:
            found.append(entry)
        index += step[index]
    if not found:
        return None                                     # urgency alone
    language, _kind, reply = next((entry for entry in found if entry[1] == GREETING), found[0])
    return SocialMatch(language, reply)


__all__ = ["DEFAULT_REPLY", "EMOJI", "GREETING_REPLIES", "MARKERS", "MAX_FREE_PUNCTUATION_RUNS", "MAX_PHRASE_WORDS",
           "MAX_PUNCTUATION_RUN",
           "MAX_SOCIAL_CHARACTERS", "MAX_SOCIAL_WORDS", "PHRASES", "PUNCTUATION", "SKIN_TONES", "SOCIAL_TABLE",
           "SocialMatch", "URGENCY_PHRASES", "fold", "social_match", "words"]
