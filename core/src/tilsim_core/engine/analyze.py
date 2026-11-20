"""Analysis: from a typed word to every reading the lexicon supports.

A reading is (lexeme, form): the lemma, part of speech and the full tag of that
form. A word can have several readings, either from different lexemes (стали:
стать / сталь) or from one lexeme whose forms coincide (книги: gen. sing. and
nom./acc. plur.). Then the status is "ambiguous" and every reading is listed;
the engine never picks one silently. A word the lexicon does not know gets
"error" with "did you mean" suggestions, never a guessed analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .grammemes import RARE_USAGE, describe
from .messages import Message
from .lexicon import Lexeme, Lexicon, WordForm, default_lexicon
from .normalize import lookup_key, normalize_word

OK, AMBIGUOUS, ERROR = "ok", "ambiguous", "error"
_ALPHABET = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"


@dataclass
class Reading:
    lexeme: Lexeme
    form: WordForm
    notes: list[Message] = field(default_factory=list)

    def to_dict(self, lang: str = "uz") -> dict:
        tag = self.form.tag
        return {
            "lexeme": self.lexeme.id,
            "lemma": self.lexeme.headword,
            "form": self.form.text,
            "form_index": self.form.index,
            "pos": tag.pos,
            "tag": tag.to_dict(),
            "description": tag.describe(lang),
            "source": "lexicon",
            "rules": ["lexicon.form"] + (["lexicon.rare_form"] if RARE_USAGE & tag.grammemes else []),
            "confidence": 1.0,
            "notes": [n.text(lang) for n in self.notes],
        }


@dataclass
class Analysis:
    input: str
    word: str
    status: str
    readings: list[Reading] = field(default_factory=list)
    warnings: list[Message] = field(default_factory=list)
    errors: list[Message] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    stress_index: int | None = None

    @property
    def lemmas(self) -> list[str]:
        return list(dict.fromkeys(r.lexeme.headword for r in self.readings))

    def to_dict(self, lang: str = "uz") -> dict:
        return {
            "input": self.input,
            "word": self.word,
            "status": self.status,
            "lemmas": self.lemmas,
            "readings": [r.to_dict(lang) for r in self.readings],
            "warnings": [w.text(lang) for w in self.warnings],
            "errors": [e.to_dict(lang) for e in self.errors],
            "suggestions": self.suggestions,
            "stress_index": self.stress_index,
        }


def _edits1(word: str) -> set[str]:
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    deletes = {a + b[1:] for a, b in splits if b}
    transposes = {a + b[1] + b[0] + b[2:] for a, b in splits if len(b) > 1}
    replaces = {a + c + b[1:] for a, b in splits if b for c in _ALPHABET}
    inserts = {a + c + b for a, b in splits for c in _ALPHABET}
    return deletes | transposes | replaces | inserts


def suggest(key: str, lexicon: Lexicon, limit: int = 5) -> list[str]:
    """Known words one edit away (typo correction). Shown as suggestions, never applied."""
    found: list[str] = []
    for candidate in sorted(_edits1(key)):
        for _, form in lexicon.lookup(lookup_key(candidate)):
            if form.text not in found:
                found.append(form.text)
        if len(found) >= limit:
            break
    return found[:limit]


def analyze(text: str, lexicon: Lexicon | None = None) -> Analysis:
    lexicon = lexicon or default_lexicon()
    normalized = normalize_word(text)
    result = Analysis(input=text, word=normalized.word, status=ERROR,
                      warnings=list(normalized.warnings), stress_index=normalized.stress_index)
    if normalized.error:
        result.errors.append(normalized.error)
        return result

    for lexeme, form in lexicon.lookup(normalized.key):
        reading = Reading(lexeme, form)
        # ё matters for pronunciation: say when it was written as е, and when it does not match.
        if "ё" in form.text and "ё" not in normalized.word and form.text.replace("ё", "е") == normalized.word:
            reading.notes.append(Message("spelled_with_yo", {"form": form.text}))
        rare = RARE_USAGE & form.tag.grammemes
        if rare:
            codes = sorted(rare)
            reading.notes.append(Message("rare_form", {"labels": lambda lang, c=codes: ", ".join(describe(g, lang) for g in c)}))
        result.readings.append(reading)

    if "ё" in normalized.word:
        exact = [r for r in result.readings if r.form.text == normalized.word]
        if exact:
            result.readings = exact

    if not result.readings:
        result.errors.append(Message("unknown_word", {"word": normalized.word}))
        result.suggestions = suggest(normalized.key, lexicon)
        return result

    # Common words first, rare and variant forms last; otherwise keep the lexicon order.
    result.readings.sort(key=lambda r: bool(RARE_USAGE & r.form.tag.grammemes))
    result.status = OK if len(result.readings) == 1 else AMBIGUOUS
    return result
