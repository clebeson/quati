"""Code-owned multilingual social table (S00_RUNTIME_CONTRACT "Displayed text and social outcomes").

A text is *social-only* when its words, in order, can be cut into phrases of ``SOCIAL_TABLE``
(greetings, pleasantries, thanks) and single ``MARKERS`` words, with at least one table phrase.
Such a text asks for nothing: the application answers it with its own deterministic template and
no model is called. Any other word puts the text outside the table.

The table is data. Matching is on whole phrases, never on a bag of words, so a question built from
words of several phrases ("que é isso?", "how is it") is not social. Words are compared after
``fold`` (Unicode NFKC and casefold); a word is a run of letters, combining marks and digits, so
scripts whose vowel signs are marks ("नमस्ते") stay one word and every other character separates.
Unaccented spellings are listed explicitly; nothing is stripped from the input.
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
        GREETING: ("ciao", "buongiorno", "buonasera", "salve"),
        PLEASANTRY: ("come stai", "come sta", "come va", "tutto bene"),
        THANKS: ("grazie", "grazie mille"),
    }),
    ("nl", None, {
        GREETING: ("hoi", "goedemorgen", "goedemiddag", "goedenavond", "goedendag"),
        PLEASANTRY: ("hoe gaat het", "hoe gaat het met je", "hoe gaat het met u"),
        THANKS: ("bedankt", "dank je", "dank je wel", "dank u"),
    }),
    ("tr", None, {
        GREETING: ("merhaba", "selam", "günaydın", "gunaydin", "iyi günler", "iyi gunler", "iyi akşamlar",
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
# Urgency words and the demonstrative or copula that carries them ("this is urgent", "it is urgent",
# "isto é urgente", "c'est urgent", "das ist dringend"). They name no object and no action; alone
# they are not social (SOC-01 negative: "urgent" in a greeting-only sentence).
MARKERS = frozenset("urgent urgently urgente dringend this is it isto isso é esto c est das ist è questo".split())


@dataclass(frozen=True)
class SocialMatch:
    """The deterministic answer to a social-only text."""

    language: str      # the language of the phrase that selected the reply
    reply: str         # application-owned template


def fold(text: str) -> str:
    """Unicode NFKC and casefold; the casefold of the Turkish dotted capital I is a plain ``i``."""
    folded = unicodedata.normalize("NFKC", unicodedata.normalize("NFKC", text).casefold())
    return folded.replace("i̇", "i")


def words(text: str) -> tuple[str, ...]:
    """Runs of letters, combining marks and digits of the folded text; anything else separates."""
    found: list[str] = []
    current: list[str] = []
    for character in fold(text):
        if unicodedata.category(character)[0] in "LMN":
            current.append(character)
        elif current:
            found.append("".join(current))
            current = []
    if current:
        found.append("".join(current))
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
MAX_PHRASE_WORDS = max(len(phrase) for phrase in PHRASES)


def social_match(text: str) -> SocialMatch | None:
    """The reply to a social-only text, or None when any word is outside the table.

    The reply is the template of the first greeting in the text; a text without a greeting
    (thanks, pleasantries) gets the template of its first phrase's language."""
    tokens = words(text)
    count = len(tokens)
    # step[i]: words of the longest table phrase (or 1 for a marker) at i from which the rest of
    # the text can still be cut; 0 when the text cannot be cut from i. Filled from the end.
    step = [0] * count + [1]
    for index in range(count - 1, -1, -1):
        for size in range(min(MAX_PHRASE_WORDS, count - index), 0, -1):
            known = tokens[index:index + size] in PHRASES or (size == 1 and tokens[index] in MARKERS)
            if known and step[index + size]:
                step[index] = size
                break
    if not count or not step[0]:
        return None
    found, index = [], 0
    while index < count:
        entry = PHRASES.get(tokens[index:index + step[index]])
        if entry is not None:
            found.append(entry)
        index += step[index]
    if not found:
        return None                                     # markers alone
    language, _kind, reply = next((entry for entry in found if entry[1] == GREETING), found[0])
    return SocialMatch(language, reply)


__all__ = ["DEFAULT_REPLY", "GREETING_REPLIES", "MARKERS", "MAX_PHRASE_WORDS", "PHRASES", "SOCIAL_TABLE",
           "SocialMatch", "fold", "social_match", "words"]
