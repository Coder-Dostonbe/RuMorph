"""Spell and grammar check of a Russian text, on the device.

The text is split into words; each word is analysed with the dictionary, and a
word right after a preposition is read in that context. What is reported, from
most to least certain:

- "error": certainly wrong as written — Latin letters inside a Cyrillic word,
  Uzbek letters (ў қ ғ ҳ) in a Russian word.
- "grammar": very likely wrong — after a preposition the word is in a case the
  preposition never takes (в школа), or a 3rd-person pronoun without н- (к ему).
  Only reported when every reading of the word has a case and none fits.
- "unknown": the word is not in the dictionary. The bundled dictionary has a few
  thousand words, so this does not mean the word is wrong; one-letter-off
  dictionary words are offered as possible corrections.
- "note": written correctly, worth knowing — е written for ё (еще → ещё).
- "repeat": the same word twice in a row (и и).

Words in Latin script only (names, brands) are left alone.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .engine.analyze import AMBIGUOUS, ERROR, OK, analyze, suggest
from .engine.context import analyze_after
from .engine.lexicon import Lexicon, default_lexicon
from .engine.messages import Message
from .engine.normalize import lookup_key

MAX_TEXT = 20000
# A word: letters (Cyrillic, Latin, Uzbek Cyrillic), a combining stress mark, inner hyphens.
_WORD = re.compile(r"[A-Za-zА-Яа-яЁёЎўҚқҒғҲҳ́]+(?:-[A-Za-zА-Яа-яЁёЎўҚқҒғҲҳ́]+)*")
_CYRILLIC = re.compile(r"[А-Яа-яЁё]")
_LATIN = re.compile(r"[A-Za-z]")


@dataclass
class Issue:
    start: int
    end: int
    word: str
    level: str                          # error | grammar | unknown | note | repeat
    messages: list[Message] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    replace: tuple[int, int] | None = None   # span the suggestions replace (two words for a phrase)

    def to_dict(self, lang: str) -> dict:
        start, end = self.replace or (self.start, self.end)
        return {"start": self.start, "end": self.end, "word": self.word, "level": self.level,
                "messages": [m.text(lang) for m in self.messages], "suggestions": self.suggestions,
                "replace_start": start, "replace_end": end}


@dataclass
class CheckResult:
    words: int
    known: int
    issues: list[Issue]

    def to_dict(self, lang: str = "uz") -> dict:
        return {"words": self.words, "known": self.known, "issues": [i.to_dict(lang) for i in self.issues]}


def check(text: str, lexicon: Lexicon | None = None) -> CheckResult:
    if len(text) > MAX_TEXT:
        raise ValueError(f"text longer than {MAX_TEXT} characters")
    lexicon = lexicon or default_lexicon()
    issues: list[Issue] = []
    words = known = 0
    previous: tuple[re.Match, object] | None = None      # (match, analysis) of the word before

    for match in _WORD.finditer(text):
        token = match.group(0)
        if not _CYRILLIC.search(token):
            previous = None                             # Latin-only: a name or brand, left alone
            continue
        words += 1
        span = (match.start(), match.end())
        result = analyze(token, lexicon)
        mixed = bool(_LATIN.search(token))
        uzbek = any(c in token for c in "ЎўҚқҒғҲҳ")

        if uzbek or (result.status == ERROR and result.errors and result.errors[0].code != "unknown_word"):
            issues.append(Issue(*span, token, "error", list(result.errors) or [], []))
            previous = None
            continue
        if mixed:
            # The engine replaced look-alike Latin letters; the word as typed is still wrong.
            fixed = result.word
            issues.append(Issue(*span, token, "error", list(result.warnings), [_like(token, fixed)] if fixed else []))
        if result.status == ERROR:
            issues.append(Issue(*span, token, "unknown", list(result.errors), [_like(token, x) for x in result.suggestions]))
        else:
            known += 1
            notes = [n for r in result.readings for n in r.notes if n.code == "spelled_with_yo"]
            if notes and all(r.notes for r in result.readings):
                issues.append(Issue(*span, token, "note", notes[:1], [_like(token, notes[0].params["form"])]))

        between = text[previous[0].end():match.start()] if previous else ""
        if previous and between.strip() == "":
            prev_match, prev_result = previous
            if lookup_key(prev_match.group(0)) == lookup_key(token):
                issues.append(Issue(*span, token, "repeat", [Message("repeated_word", {"word": token})], []))
            elif result.status in (OK, AMBIGUOUS) and _is_preposition(prev_result):
                issue = _government(prev_match, match, result)
                if issue:
                    issues.append(issue)
        previous = (match, result)

    issues.sort(key=lambda i: (i.start, i.level))
    return CheckResult(words, known, issues)


def _like(original: str, suggestion: str) -> str:
    """The suggestion with the original's capital first letter (Еще → Ещё, К ему → К нему)."""
    if original[:1].isupper() and suggestion[:1].islower():
        return suggestion[:1].upper() + suggestion[1:]
    return suggestion


def _is_preposition(result) -> bool:
    """Only words that are prepositions and never adverbs: вокруг, после, около … can stand alone
    as adverbs (вокруг тишина), and then the next word is not governed by them."""
    pos = {r.form.tag.pos for r in result.readings}
    return result.status in (OK, AMBIGUOUS) and "PREP" in pos and "ADVB" not in pos


def _government(prep: re.Match, word: re.Match, result) -> Issue | None:
    """A grammar issue when every reading of the word has a case and the preposition takes none of them."""
    if any(r.form.tag.case is None for r in result.readings):
        return None                                      # an adverb or a verb may follow: not checked
    phrase = analyze_after(prep.group(0), word.group(0))
    if phrase.status != ERROR or not phrase.errors:
        return None
    if phrase.errors[0].code not in ("wrong_case_after_preposition", "needs_n_form"):
        return None
    return Issue(word.start(), word.end(), word.group(0), "grammar", list(phrase.errors),
                 [_like(prep.group(0), x) for x in phrase.suggestions], replace=(prep.start(), word.end()))


__all__ = ["CheckResult", "Issue", "MAX_TEXT", "check", "suggest"]
