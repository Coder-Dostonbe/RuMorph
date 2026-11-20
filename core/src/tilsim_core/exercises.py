"""Exercises generated from the lexicon: multiple-choice questions with exactly one right answer.

Kinds:
- case_form: the form of a noun in a given case and number (книга → genitive plural: книг).
- conjugation: the present / simple-future form of a verb for a person and number (писать → я: пишу).
- gender: the gender of a noun (книга → feminine).
- preposition: the form of a noun after a preposition that takes one case (без + книга → книги).
- aspect: whether a verb is imperfective or perfective.
- translation: the learner's own translation of one of their words (needs at least 4 of them).

Every answer comes from the dictionary, never from a rule applied by guess. A question is only
made when its answer is unambiguous: the distractors are other real forms of the same word that
differ from every right form, and words whose right form is not unique (variants, two genders,
two aspects) are skipped. Questions are made with a seeded random generator, so a seed gives the
same test again.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .engine.classify import classify
from .engine.grammemes import NOT_MAIN
from .engine.lexicon import Lexeme, Lexicon, default_lexicon
from .engine.prepositions import CASE_VARIANTS, PREPOSITIONS
from .engine.search import ranks

KINDS = ("case_form", "conjugation", "gender", "preposition", "aspect", "translation")
CASES = ("nomn", "gent", "datv", "accs", "ablt", "loct")
GENDERS = ("masc", "femn", "neut")
PERSONS = (("1per", "sing"), ("2per", "sing"), ("3per", "sing"), ("1per", "plur"), ("2per", "plur"), ("3per", "plur"))
SKIP = tuple(NOT_MAIN)


@dataclass
class Question:
    kind: str
    lexeme: str                      # lexeme id
    lemma: str
    prompt: dict                     # kind-specific: grammemes, preposition, …
    options: list[str]
    answer: int
    rule: str | None = None          # the rule that explains the answer, when there is one
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"kind": self.kind, "lexeme": self.lexeme, "lemma": self.lemma, "prompt": self.prompt,
                "options": self.options, "answer": self.answer, "rule": self.rule, **self.extra}


def _texts(lexeme: Lexeme, *grammemes: str) -> list[str]:
    return list(dict.fromkeys(f.text for f in lexeme.find(*grammemes, exclude=SKIP)))


def _all_texts(lexeme: Lexeme, pos: str) -> list[str]:
    return list(dict.fromkeys(f.text for f in lexeme.forms if f.tag.pos == pos and not (set(SKIP) & f.tag.grammemes)))


def _choice(rng: random.Random, right: str, wrong: list[str], n: int = 4) -> tuple[list[str], int] | None:
    wrong = [w for w in dict.fromkeys(wrong) if w != right]
    if len(wrong) < n - 1:
        return None
    options = rng.sample(wrong, n - 1) + [right]
    rng.shuffle(options)
    return options, options.index(right)


def _pool(lexicon: Lexicon, pos: str, max_rank: int) -> list[Lexeme]:
    rank = ranks(lexicon)
    return sorted((lx for lx in lexicon.lexemes.values()
                   if lx.pos == pos and rank.get(lx.id, 10**9) <= max_rank and "Fixd" not in lx.lemma_tag
                   and not (set(SKIP) & lx.lemma_tag.grammemes)), key=lambda lx: lx.id)


def _rule(lexeme: Lexeme) -> str | None:
    profile = classify(lexeme)
    return profile.category if profile else None


def case_form(lexeme: Lexeme, rng: random.Random) -> Question | None:
    numbers = [n for n in ("sing", "plur") if _texts(lexeme, n, "nomn")]
    if not numbers:
        return None
    number, case = rng.choice(numbers), rng.choice(CASES[1:])
    right = _texts(lexeme, "NOUN", number, case)
    if len(right) != 1:
        return None
    every_right = {f.text for f in lexeme.find(number, case)}       # variants too: never a distractor
    made = _choice(rng, right[0], [t for t in _all_texts(lexeme, "NOUN") if t not in every_right])
    if not made:
        return None
    return Question("case_form", lexeme.id, lexeme.headword, {"grammemes": [case, number]}, made[0], made[1], _rule(lexeme))


def conjugation(lexeme: Lexeme, rng: random.Random) -> Question | None:
    aspects = {a for f in lexeme.forms for a in ("impf", "perf") if a in f.tag}
    if len(aspects) != 1:
        return None
    tense = "pres" if aspects == {"impf"} else "futr"
    person, number = rng.choice(PERSONS)
    right = _texts(lexeme, "VERB", "indc", tense, person, number)
    if len(right) != 1:
        return None
    finite = [f.text for f in lexeme.find("VERB", "indc", tense, exclude=SKIP)]
    finite += [f.text for f in lexeme.find("VERB", "indc", "past", exclude=SKIP)]
    every_right = {f.text for f in lexeme.find("VERB", "indc", tense, person, number)}
    made = _choice(rng, right[0], [t for t in finite if t not in every_right])
    if not made:
        return None
    return Question("conjugation", lexeme.id, lexeme.lemma, {"grammemes": [tense, person, number]},
                    made[0], made[1], _rule(lexeme))


def gender(lexeme: Lexeme, rng: random.Random) -> Question | None:
    tag = lexeme.lemma_tag
    genders = [g for g in GENDERS if g in tag]
    if len(genders) != 1 or "Pltm" in tag or not _texts(lexeme, "sing", "nomn"):
        return None
    options = list(GENDERS)
    return Question("gender", lexeme.id, lexeme.headword, {}, options, options.index(genders[0]), _rule(lexeme),
                    {"option_kind": "grammeme"})


# Prepositions that take one case in all their ordinary uses: the right form is unique.
ONE_CASE = sorted(p for p, governs in PREPOSITIONS.items()
                  if len([g for g in governs if not g.rare]) == 1 and p not in ("несмотря",))


_VOWELS = "аоуэиыеёюя"
# Before some consonant clusters these take an extra -о (ко мне, изо рта, ото всех) and usage
# varies; such questions are not made.
_MAY_ADD_O = {"к", "из", "от", "без", "над", "перед", "под", "в", "с"}


def _shown_preposition(prep: str, answer: str) -> str | None:
    """The preposition as it is written before this form (о окне → об окне), or None when the
    written form is not certain."""
    if prep == "о":
        return "об" if answer[0] in "аоуэи" else "о"
    if prep in _MAY_ADD_O and len(answer) > 1 and answer[0] not in _VOWELS and answer[1] not in _VOWELS:
        return None
    return prep


def preposition(lexeme: Lexeme, rng: random.Random) -> Question | None:
    prep = rng.choice(ONE_CASE)
    case = next(g.case for g in PREPOSITIONS[prep] if not g.rare)
    number = "sing" if _texts(lexeme, "sing", "nomn") else "plur"
    right = [t for c in CASE_VARIANTS[case][:1] for t in _texts(lexeme, "NOUN", number, c)]
    if len(right) != 1:
        return None
    shown = _shown_preposition(prep, right[0])
    if shown is None:
        return None
    # Not a distractor: any form the preposition can take, in either number and in set phrases too
    # (через науки is right as a plural; между + genitive exists in set phrases).
    governed = {c for g in PREPOSITIONS[prep] for c in CASE_VARIANTS[g.case]}
    every_right = {f.text for f in lexeme.forms if f.tag.case in governed}
    others = [t for t in _texts(lexeme, "NOUN", number) if t not in every_right]
    made = _choice(rng, right[0], others)
    if not made:
        return None
    nominative = _texts(lexeme, number, "nomn")
    return Question("preposition", lexeme.id, nominative[0] if nominative else lexeme.headword,
                    {"preposition": shown, "case": case, "grammemes": [number]}, made[0], made[1], None)


def aspect(lexeme: Lexeme, rng: random.Random) -> Question | None:
    aspects = {a for f in lexeme.forms for a in ("impf", "perf") if a in f.tag}
    if len(aspects) != 1:
        return None
    options = ["impf", "perf"]
    return Question("aspect", lexeme.id, lexeme.lemma, {}, options, options.index(aspects.pop()), None,
                    {"option_kind": "grammeme"})


def translation(word: dict, others: list[str], rng: random.Random) -> Question | None:
    made = _choice(rng, word["translation"], others)
    if not made:
        return None
    return Question("translation", word["lexeme_id"], word["lemma"], {}, made[0], made[1], None)


MAKERS = {"case_form": ("NOUN", case_form), "conjugation": ("INFN", conjugation), "gender": ("NOUN", gender),
          "preposition": ("NOUN", preposition), "aspect": ("INFN", aspect)}


def generate(kind: str, count: int, seed: int, *, max_rank: int = 1000, vocabulary: list[dict] | None = None,
             lexicon: Lexicon | None = None) -> list[Question]:
    """Up to `count` questions of one kind (fewer when there are not enough suitable words)."""
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    rng = random.Random(seed)
    if kind == "translation":
        words = [w for w in (vocabulary or []) if str(w.get("translation", "")).strip()]
        texts = list(dict.fromkeys(w["translation"].strip() for w in words))
        rng.shuffle(words)
        out = []
        for word in words:
            q = translation({**word, "translation": word["translation"].strip()}, texts, rng)
            if q:
                out.append(q)
            if len(out) == count:
                break
        return out
    lexicon = lexicon or default_lexicon()
    pos, make = MAKERS[kind]
    pool = _pool(lexicon, pos, max_rank)
    rng.shuffle(pool)
    out, used = [], set()
    for lexeme in pool:
        if lexeme.headword in used:
            continue
        q = make(lexeme, rng)
        if q is not None:
            out.append(q)
            used.add(lexeme.headword)
        if len(out) == count:
            break
    return out
