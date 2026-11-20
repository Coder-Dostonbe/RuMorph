"""Cleans up a typed word before analysis, without losing what was typed.

- Unicode NFC; letter case is folded for lookup, the original is kept.
- A stress mark (U+0301 after a vowel) is removed and its position recorded.
- Latin letters that look like Cyrillic ones (a, e, o, p, c, x, …) inside a
  Cyrillic word are replaced, with a warning: a common mistake when switching
  keyboard layouts.
- ё and е: the dictionary writes ё; texts often write е. The lookup key folds
  ё to е and the analysis reports when ё was missing.
- Uzbek-only Cyrillic letters (ў, қ, ғ, ҳ) and Uzbek Latin text are refused
  with an explanation instead of being looked up as Russian.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from .messages import Message

STRESS = "́"
GRAVE = "̀"
VOWELS = "аеёиоуыэюя"
RUSSIAN_LETTERS = set("абвгдеёжзийклмнопрстуфхцчшщъыьэюя")
UZBEK_ONLY = set("ўқғҳ")
# Latin letters that are drawn like Cyrillic ones (keyboard-layout mistakes).
HOMOGLYPHS = str.maketrans({"a": "а", "e": "е", "o": "о", "p": "р", "c": "с", "x": "х", "y": "у",
                            "k": "к", "m": "м", "t": "т", "h": "н", "b": "в"})
HYPHENS = str.maketrans({"‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-"})
MAX_LENGTH = 60


@dataclass
class Normalized:
    original: str
    word: str = ""                 # lower case, NFC, no stress marks; ё kept as typed
    key: str = ""                  # lookup key: like `word`, with ё folded to е
    stress_index: int | None = None  # index in `word` of the vowel the user marked as stressed
    warnings: list[Message] = field(default_factory=list)
    error: Message | None = None

    @property
    def error_code(self) -> str | None:
        return self.error.code if self.error else None


def lookup_key(word: str) -> str:
    return word.lower().replace("ё", "е")


def normalize_word(text: str) -> Normalized:
    result = Normalized(original=text)
    value = unicodedata.normalize("NFC", text).strip().translate(HYPHENS)
    if not value:
        result.error = Message("empty")
        return result
    if any(ch.isspace() for ch in value):
        result.error = Message("several_words")
        return result
    if len(value) > MAX_LENGTH:
        result.error = Message("too_long", {"limit": MAX_LENGTH})
        return result

    # Stress marks: keep the position of the marked vowel, then drop the mark.
    decomposed = unicodedata.normalize("NFD", value)
    letters: list[str] = []
    for ch in decomposed:
        if ch in (STRESS, GRAVE):
            if letters and letters[-1].lower() in VOWELS + "еи":
                result.stress_index = len(letters) - 1
            continue
        letters.append(ch)
    value = unicodedata.normalize("NFC", "".join(letters))
    lowered = value.lower()

    if set(lowered) & UZBEK_ONLY:
        result.error = Message("uzbek_letters")
        return result

    has_cyrillic = any(ch in RUSSIAN_LETTERS for ch in lowered)
    latin = [ch for ch in lowered if "a" <= ch <= "z"]
    if latin and not has_cyrillic:
        result.error = Message("latin_script")
        return result
    if latin:
        fixed = lowered.translate(HOMOGLYPHS)
        if any("a" <= ch <= "z" for ch in fixed):
            result.error = Message("mixed_script")
            return result
        result.warnings.append(Message("latin_replaced", {"letters": "".join(sorted(set(latin))), "fixed": fixed}))
        lowered = fixed

    if not re.fullmatch(r"[а-яё]+(?:-[а-яё]+)*", lowered):
        result.error = Message("invalid_characters")
        return result

    result.word = lowered
    result.key = lookup_key(lowered)
    return result
