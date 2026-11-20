"""Paradigm tables for the app: a lexeme's forms arranged the way a grammar book
shows them.

- noun: cases × numbers;
- adjective (and pronouns that agree with a noun, and participles): cases ×
  genders and plural, accusative split into animate / inanimate;
- pronoun: cases × "plain / after a preposition";
- verb: infinitive, present or future by person, past by gender, imperative,
  participles (each with its own adjective grid) and gerunds.

Every form of the lexeme appears somewhere: forms that do not fit the main grid
(second genitive, rare variants, …) go to `extra`, so nothing the dictionary
knows is hidden. The one constructed entry is the compound future of an
imperfective verb (буду читать): it is built from быть and the infinitive,
marked as such, and has no form index.
"""

from __future__ import annotations

from collections.abc import Iterable

from .grammemes import NOT_MAIN, RARE_USAGE
from .lexicon import Lexeme, Lexicon, WordForm

VARIANT = NOT_MAIN - RARE_USAGE      # -ою, -ею, literary forms: correct, but not the usual one
CASES = ("nomn", "gent", "datv", "accs", "ablt", "loct")
EXTRA_CASES = ("gen2", "loc2", "voct", "acc2")
PERSONS = ("1per", "2per", "3per")
GENDERS_PLURAL = ("masc", "neut", "femn", "plur")


def _cell(forms: Iterable[WordForm]) -> list[dict]:
    """One entry per distinct text. When the same text is several forms of the lexeme (бежать is
    both perfective and imperfective in one paradigm), the other indices go to "also"."""
    seen: dict[str, dict] = {}
    for f in forms:
        if f.text not in seen:
            seen[f.text] = {"form": f.text, "index": f.index, "rare": bool(RARE_USAGE & f.tag.grammemes),
                            "variant": bool(VARIANT & f.tag.grammemes)}
        else:
            seen[f.text].setdefault("also", []).append(f.index)
    return sorted(seen.values(), key=lambda c: (c["rare"], c["variant"]))


def _extra(lexeme: Lexeme, used: set[int]) -> list[dict]:
    return [{"form": f.text, "index": f.index, "tag": f.tag.text, "rare": bool(RARE_USAGE & f.tag.grammemes)}
            for f in lexeme.forms if f.index not in used]


def _select(forms: Iterable[WordForm], *grammemes: str, exclude: tuple[str, ...] = ()) -> list[WordForm]:
    return [f for f in forms if all(g in f.tag for g in grammemes) and not any(g in f.tag for g in exclude)]


def noun_table(lexeme: Lexeme) -> dict:
    columns = [n for n in ("sing", "plur") if lexeme.find(n)]
    used: set[int] = set()
    rows = []
    for case in CASES + EXTRA_CASES:
        cells = []
        for number in columns:
            forms = lexeme.find(number, case)
            used.update(f.index for f in forms)
            cells.append(_cell(forms))
        if case in CASES or any(cells):
            rows.append({"key": case, "cells": cells})
    return {"kind": "noun", "columns": columns, "rows": rows, "extra": _extra(lexeme, used)}


def _agreement_grid(forms: list[WordForm], used: set[int]) -> list[dict]:
    """Rows of cases, columns masc / neut / femn / plur; the accusative split by animacy."""
    def pick(case: str, column: str, animacy: str | None = None) -> list[dict]:
        if column == "plur":
            found = _select(forms, "plur", case)
        else:
            found = _select(forms, "sing", column, case)
        if animacy:
            marked = [f for f in found if animacy in f.tag]
            found = marked or [f for f in found if "anim" not in f.tag and "inan" not in f.tag]
        used.update(f.index for f in found)
        return _cell(found)

    rows = []
    for case in CASES if forms else ():
        if case == "accs":
            rows.append({"key": "accs.anim", "cells": [pick(case, c, "anim") for c in GENDERS_PLURAL]})
            rows.append({"key": "accs.inan", "cells": [pick(case, c, "inan") for c in GENDERS_PLURAL]})
        else:
            rows.append({"key": case, "cells": [pick(case, c) for c in GENDERS_PLURAL]})
    return rows


def _short_row(forms: list[WordForm], used: set[int]) -> list[list[dict]] | None:
    cells = []
    for column in GENDERS_PLURAL:
        found = _select(forms, column)
        used.update(f.index for f in found)
        cells.append(_cell(found))
    return cells if any(cells) else None


def adjective_table(lexeme: Lexeme) -> dict:
    """Full forms in the grid, short forms in one row, the comparative apart.

    Synthetic superlatives (новейший, наиновейший) are separate lexical forms in
    OpenCorpora; they are kept out of the grid and listed under `extra`.
    """
    used: set[int] = set()
    full = [f for f in lexeme.forms if f.tag.pos == "ADJF" and "Supr" not in f.tag]
    rows = _agreement_grid(full, used)
    short = _short_row(lexeme.find("ADJS"), used)
    comparative = lexeme.find("COMP")
    used.update(f.index for f in comparative)
    return {
        "kind": "adjective",
        "columns": list(GENDERS_PLURAL),
        "rows": rows,
        "short": short,
        "comparative": _cell(comparative) or None,
        "extra": _extra(lexeme, used),
    }


def pronoun_table(lexeme: Lexeme) -> dict:
    """Cases in rows. The н- forms used after a preposition (него, ней, них) get their own column;
    a missing case (себя has no nominative) is an empty cell."""
    columns = ["form", "after_prep"] if lexeme.find("Af-p") else ["form"]
    used: set[int] = set()
    rows = []
    for case in CASES:
        plain = lexeme.find(case, exclude=("Af-p",))
        cells = [_cell(plain)]
        used.update(f.index for f in plain)
        if len(columns) == 2:
            after = lexeme.find(case, "Af-p")
            used.update(f.index for f in after)
            cells.append(_cell(after))
        rows.append({"key": case, "cells": cells})
    return {"kind": "pronoun", "columns": columns, "rows": rows, "extra": _extra(lexeme, used)}


# --- Verbs ------------------------------------------------------------------------------------

PARTICIPLES = (("pres", "actv"), ("past", "actv"), ("pres", "pssv"), ("past", "pssv"))


def _person_rows(forms: list[WordForm], used: set[int]) -> list[dict]:
    rows = []
    for person in PERSONS:
        cells = []
        for number in ("sing", "plur"):
            found = _select(forms, person, number)
            used.update(f.index for f in found)
            cells.append(_cell(found))
        rows.append({"key": person, "cells": cells})
    return rows


def _compound_future(lexeme: Lexeme, auxiliary: Lexeme | None) -> list[dict] | None:
    """буду / будешь / … + infinitive, for imperfective verbs other than быть itself."""
    if auxiliary is None or _aspect(lexeme) not in ("impf", "both") or lexeme.lemma == auxiliary.lemma:
        return None
    infinitive = lexeme.form("INFN", exclude=tuple(NOT_MAIN))
    if infinitive is None:
        return None
    rows = []
    for person in PERSONS:
        cells = []
        for number in ("sing", "plur"):
            aux = auxiliary.form("VERB", "futr", "indc", person, number, exclude=tuple(NOT_MAIN))
            cells.append([{"form": f"{aux.text} {infinitive.text}", "constructed": True,
                           "rule": "verb.future_compound"}] if aux else [])
        rows.append({"key": person, "cells": cells})
    return rows


def _aspect(lexeme: Lexeme) -> str | None:
    """"impf", "perf", or "both" for a two-aspect verb (бежать: run / escape) whose paradigm has both."""
    found = {a for f in lexeme.forms for a in ("impf", "perf") if a in f.tag}
    return "both" if len(found) == 2 else next(iter(found), None)


def verb_table(lexeme: Lexeme, auxiliary: Lexeme | None = None) -> dict:
    used: set[int] = set()
    tag = lexeme.lemma_tag
    infinitive = lexeme.find("INFN")
    used.update(f.index for f in infinitive)

    finite = [f for f in lexeme.forms if f.tag.pos == "VERB"]
    indicative = _select(finite, "indc")
    nonpast = []
    for tense in ("pres", "futr"):
        forms = _select(indicative, tense)
        if forms:
            nonpast.append({"tense": tense, "columns": ["sing", "plur"], "rows": _person_rows(forms, used)})

    past_forms = _select(indicative, "past")
    past = []
    for column in ("masc", "femn", "neut", "plur"):
        found = _select(past_forms, "plur") if column == "plur" else _select(past_forms, "sing", column)
        used.update(f.index for f in found)
        past.append(_cell(found))

    imperative_forms = _select(finite, "impr")
    imperative = []
    for key in ("excl", "incl"):
        cells = []
        for number in ("sing", "plur"):
            found = _select(imperative_forms, key, number)
            used.update(f.index for f in found)
            cells.append(_cell(found))
        if any(cells):
            imperative.append({"key": key, "cells": cells})

    participles = []
    for tense, voice in PARTICIPLES:
        full = [f for f in lexeme.forms if f.tag.pos == "PRTF" and tense in f.tag and voice in f.tag]
        short = [f for f in lexeme.forms if f.tag.pos == "PRTS" and tense in f.tag and voice in f.tag]
        if not full and not short:
            continue
        lemma = _cell(_select(full, "masc", "sing", "nomn"))
        participles.append({
            "key": f"{tense}.{voice}",
            "lemma": lemma,
            "columns": list(GENDERS_PLURAL),
            "rows": _agreement_grid(full, used),
            "short": _short_row(short, used),
        })

    gerunds = []
    for tense in ("pres", "past"):
        found = [f for f in lexeme.forms if f.tag.pos == "GRND" and tense in f.tag]
        used.update(f.index for f in found)
        if found:
            gerunds.append({"key": tense, "cells": _cell(found)})

    return {
        "kind": "verb",
        "aspect": _aspect(lexeme),
        "transitivity": next((t for t in ("tran", "intr") if t in tag), None),
        "infinitive": _cell(infinitive),
        "nonpast": nonpast,
        "future_compound": _compound_future(lexeme, auxiliary),
        "past": {"columns": ["masc", "femn", "neut", "plur"], "cells": past} if any(past) else None,
        "imperative": imperative,
        "participles": participles,
        "gerunds": gerunds,
        "extra": _extra(lexeme, used),
    }


def form_list(lexeme: Lexeme) -> dict:
    """Any other part of speech: every form with its tag."""
    return {"kind": "list", "extra": _extra(lexeme, set())}


def paradigm_table(lexeme: Lexeme, lexicon: Lexicon | None = None) -> dict:
    """`lexicon` supplies быть for the compound future of imperfective verbs; without it (or if the
    lexicon has no быть) that part is None rather than guessed."""
    pos = lexeme.pos
    if pos == "NOUN":
        return noun_table(lexeme)
    if pos == "NPRO":
        return pronoun_table(lexeme)
    if pos in ("ADJF", "ADJS"):
        return adjective_table(lexeme)
    if pos in ("INFN", "VERB"):
        auxiliary = next((lx for lx in lexicon.by_lemma("быть") if lx.pos == "INFN"), None) if lexicon else None
        return verb_table(lexeme, auxiliary)
    return form_list(lexeme)
