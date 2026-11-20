"""Analysis in context: a preposition and the word after it.

The preposition narrows the word's readings to the cases it governs
(prepositions.py): книги after без is only the genitive singular. What is left
decides the status, as in analyze: one reading → "ok", several (в + a word
that is both accusative and prepositional, or в with its two meanings) →
"ambiguous" with every reading and its meaning, none → "error" with the forms
of the same word that would be right.

After a preposition the 3rd-person pronouns take н- (у него). A form without
н- (у его) is right only when его means "his" (у его брата), so it is not
accepted as the pronoun; the error names the н- form.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .analyze import AMBIGUOUS, ERROR, OK, Analysis, Reading, analyze
from .grammemes import NOT_MAIN, describe
from .lexicon import Lexicon, default_lexicon
from .messages import Message
from .prepositions import CASE_VARIANTS, Government, governed

INFLECTED = ("NOUN", "NPRO", "ADJF", "NUMR", "PRTF")


@dataclass
class GovernedReading:
    reading: Reading
    government: Government

    def to_dict(self, lang: str) -> dict:
        data = self.reading.to_dict(lang)
        data["government"] = self.government.to_dict(lang)
        if self.government.rare:
            data["notes"].append(Message("rare_government", {"example": self.government.example}).text(lang))
        return data


@dataclass
class PhraseAnalysis:
    preposition: str
    word: Analysis
    status: str
    readings: list[GovernedReading] = field(default_factory=list)
    errors: list[Message] = field(default_factory=list)
    notes: list[Message] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    governs: tuple[Government, ...] = ()

    def to_dict(self, lang: str = "uz") -> dict:
        return {
            "preposition": self.preposition,
            "word": self.word.word,
            "status": self.status,
            "governs": [g.to_dict(lang) for g in self.governs],
            "readings": [r.to_dict(lang) for r in self.readings],
            "warnings": [w.text(lang) for w in self.word.warnings] + [n.text(lang) for n in self.notes],
            "errors": [e.to_dict(lang) for e in self.errors],
            "suggestions": self.suggestions,
        }


def _government_for(reading: Reading, governs: tuple[Government, ...]) -> Government | None:
    tag = reading.form.tag
    for g in governs:
        if any(c in tag for c in CASE_VARIANTS[g.case]):
            return g
    return None


def _case_names(governs: tuple[Government, ...], lang: str) -> str:
    return ", ".join(describe(g.case, lang) for g in governs if not g.rare)


def analyze_after(preposition: str, word: str, lexicon: Lexicon | None = None) -> PhraseAnalysis:
    lexicon = lexicon or default_lexicon()
    prep = analyze(preposition, lexicon)
    prep_lemmas = [r.lexeme.lemma for r in prep.readings if r.form.tag.pos == "PREP"]
    target = analyze(word, lexicon)
    result = PhraseAnalysis(preposition=prep.word or preposition, word=target, status=ERROR)

    lemma = next((p for p in prep_lemmas if governed(p)), None)
    if lemma is None:
        result.errors.append(prep.errors[0] if prep.errors else Message("not_a_preposition", {"word": prep.word}))
        return result
    governs = governed(lemma)
    result.governs = governs
    if target.status == ERROR:
        result.errors.extend(target.errors)
        result.suggestions = target.suggestions
        return result

    with_case = [r for r in target.readings if r.form.tag.pos in INFLECTED]
    if not with_case:
        result.errors.append(Message("no_case_after_preposition", {"word": target.word, "prep": result.preposition}))
        return result

    needs_n: list[Reading] = []
    for reading in with_case:
        government = _government_for(reading, governs)
        if government is None:
            continue
        lexeme = reading.lexeme
        if lexeme.find("Af-p") and "Af-p" not in reading.form.tag:
            needs_n.append(reading)
            continue
        result.readings.append(GovernedReading(reading, government))

    if result.readings and needs_n:
        # у его: not the pronoun (that is у него), but right as the possessive "his" before a noun
        # (у его брата). Both are said, and the result is not "ok" on its own.
        fixed = _n_forms(needs_n)
        result.notes.append(Message("needs_n_form", {"prep": result.preposition, "fixed": ", ".join(fixed)}))
        result.notes.append(Message("possessive_without_n", {"word": target.word}))
        result.suggestions = [f"{result.preposition} {f}" for f in fixed]
        result.status = AMBIGUOUS
        return result

    if result.readings:
        # A set-phrase construction (по колено) is shown only when no ordinary one fits:
        # по улице is the dative, not also "после улицы".
        ordinary = [r for r in result.readings if not r.government.rare]
        result.readings = ordinary or result.readings
        result.status = OK if len(result.readings) == 1 else AMBIGUOUS
        return result

    if needs_n:
        fixed = _n_forms(needs_n)
        result.errors.append(Message("needs_n_form", {"prep": result.preposition, "fixed": ", ".join(fixed)}))
        # его / её / их (genitive) are also the possessives "his, her, their", which never take н-.
        if any(r.form.tag.case == "gent" for r in needs_n):
            result.errors.append(Message("possessive_without_n", {"word": target.word}))
        result.suggestions = [f"{result.preposition} {f}" for f in fixed]
        return result

    result.errors.append(Message("wrong_case_after_preposition", {
        "prep": result.preposition, "word": target.word, "cases": lambda lang: _case_names(governs, lang)}))
    result.suggestions = _right_forms(with_case, governs, result.preposition)
    return result


def _n_forms(readings: list[Reading]) -> list[str]:
    """The н- form in the same case as the typed one: у его → у него, к ему → к нему."""
    return list(dict.fromkeys(f.text for r in readings
                              for f in r.lexeme.find("Af-p", r.form.tag.case, exclude=tuple(NOT_MAIN))))


def _right_forms(readings: list[Reading], governs: tuple[Government, ...], prep: str) -> list[str]:
    """The same word in the cases the preposition takes, same number (and gender) as typed:
    в школа → в школу, в школе. The pronoun forms after a preposition are the н- ones."""
    out: list[str] = []
    for reading in readings:
        tag = reading.form.tag
        keep = [g for g in ("sing", "plur", "masc", "femn", "neut") if g in tag]
        for g in governs:
            if g.rare:
                continue
            exclude = tuple(NOT_MAIN)
            forms = [f for c in CASE_VARIANTS[g.case][:1]
                     for f in reading.lexeme.find(c, *keep, exclude=exclude)]
            if reading.lexeme.find("Af-p"):
                forms = [f for f in forms if "Af-p" in f.tag] or forms
            for f in forms:
                text = f"{prep} {f.text}"
                if text not in out:
                    out.append(text)
    return out[:6]
