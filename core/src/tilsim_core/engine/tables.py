"""Paradigm tables for the app: a lexeme's forms arranged the way a grammar book
shows them (cases × numbers for nouns, cases × genders for adjectives and
pronouns that agree with a noun, cases × "plain / after a preposition" for the
other pronouns).

Every form of the lexeme appears somewhere: forms that do not fit the main grid
(second genitive, rare variants, participles of a verb, …) go to `extra`, so
nothing the dictionary knows is hidden.
"""

from __future__ import annotations

from .grammemes import NOT_MAIN, RARE_USAGE

VARIANT = NOT_MAIN - RARE_USAGE      # -ою, -ею, literary forms: correct, but not the usual one
from .lexicon import Lexeme, WordForm

CASES = ("nomn", "gent", "datv", "accs", "ablt", "loct")
EXTRA_CASES = ("gen2", "loc2", "voct", "acc2")


def _cell(forms: list[WordForm]) -> list[dict]:
    seen: dict[str, dict] = {}
    for f in forms:
        if f.text not in seen:
            seen[f.text] = {"form": f.text, "index": f.index, "rare": bool(RARE_USAGE & f.tag.grammemes),
                            "variant": bool(VARIANT & f.tag.grammemes)}
    return sorted(seen.values(), key=lambda c: (c["rare"], c["variant"]))


def _extra(lexeme: Lexeme, used: set[int]) -> list[dict]:
    return [{"form": f.text, "index": f.index, "tag": f.tag.text, "rare": bool(RARE_USAGE & f.tag.grammemes)}
            for f in lexeme.forms if f.index not in used]


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


def adjective_table(lexeme: Lexeme) -> dict:
    """Full forms: masc / neut / femn / plur × cases; accusative split into animate / inanimate.

    Synthetic superlatives (новейший, наиновейший) are separate lexical forms in
    OpenCorpora; they are kept out of the grid and listed under `extra`.
    """
    columns = ["masc", "neut", "femn", "plur"]
    used: set[int] = set()

    def pick(case: str, column: str, animacy: str | None = None) -> list[dict]:
        if column == "plur":
            forms = lexeme.find("ADJF", "plur", case, exclude=("Supr",)) or \
                lexeme.find("plur", case, exclude=("ADJS", "COMP", "Supr"))
        else:
            forms = lexeme.find("ADJF", "sing", column, case, exclude=("Supr",)) or \
                lexeme.find("sing", column, case, exclude=("ADJS", "COMP", "Supr"))
        if animacy:
            marked = [f for f in forms if animacy in f.tag]
            forms = marked or [f for f in forms if "anim" not in f.tag and "inan" not in f.tag]
        used.update(f.index for f in forms)
        return _cell(forms)

    rows = []
    for case in CASES if lexeme.find("ADJF") else ():
        if case == "accs":
            rows.append({"key": "accs.anim", "cells": [pick(case, c, "anim") for c in columns]})
            rows.append({"key": "accs.inan", "cells": [pick(case, c, "inan") for c in columns]})
        else:
            rows.append({"key": case, "cells": [pick(case, c) for c in columns]})

    short = []
    for column in ("masc", "neut", "femn", "plur"):
        forms = lexeme.find("ADJS", column) if column != "plur" else lexeme.find("ADJS", "plur")
        used.update(f.index for f in forms)
        short.append(_cell(forms))
    comparative = lexeme.find("COMP")
    used.update(f.index for f in comparative)
    return {
        "kind": "adjective",
        "columns": columns,
        "rows": rows,
        "short": short if any(short) else None,
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


def form_list(lexeme: Lexeme) -> dict:
    """Any other part of speech (verbs get their own table in step 2.5): every form with its tag."""
    return {"kind": "list", "extra": _extra(lexeme, set())}


def paradigm_table(lexeme: Lexeme) -> dict:
    pos = lexeme.pos
    if pos == "NOUN":
        return noun_table(lexeme)
    if pos == "NPRO":
        return pronoun_table(lexeme)
    if pos in ("ADJF", "ADJS"):
        return adjective_table(lexeme)
    return form_list(lexeme)
