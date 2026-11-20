"""Dictionary search over the lexicon.

- A typed form finds its lexemes (книги → книга), as in analysis.
- A beginning finds every word whose dictionary form starts with it (кни → книга, книжный).
- No query lists the words by frequency, most frequent first, for browsing.

Results are ordered by frequency (wordfreq). Each carries its frequency rank in
the lexicon (1 = most frequent), which the app turns into "among the 500 /
1000 / … most frequent words". Only Cyrillic is searched here; the app
searches the user's Uzbek translations itself.
"""

from __future__ import annotations

from dataclasses import dataclass

from .lexicon import Lexeme, Lexicon, default_lexicon
from .normalize import lookup_key

POS_FILTERS = ("NOUN", "ADJF", "VERB", "ADVB", "NPRO", "NUMR", "PREP", "CONJ", "PRCL", "PRED", "INTJ")
_CYRILLIC = set("абвгдеёжзийклмнопрстуфхцчшщъыьэюя-")


@dataclass(frozen=True)
class Hit:
    lexeme: Lexeme
    rank: int | None
    match: str            # "form" | "prefix" | "browse"


def _pos_group(lexeme: Lexeme) -> str | None:
    pos = lexeme.pos
    return "VERB" if pos == "INFN" else "ADJF" if pos == "ADJS" else pos


def ranks(lexicon: Lexicon) -> dict[str, int]:
    """Lexeme id → frequency rank (1 = most frequent); lexemes without a frequency are not ranked."""
    cached = getattr(lexicon, "_ranks", None)
    if cached is None:
        ordered = sorted((lx for lx in lexicon.lexemes.values() if lx.freq is not None),
                         key=lambda lx: (-(lx.freq or 0.0), lx.id))
        cached = {lx.id: n for n, lx in enumerate(ordered, 1)}
        lexicon._ranks = cached        # type: ignore[attr-defined]
    return cached


def search(query: str, lexicon: Lexicon | None = None, *, pos: str | None = None,
           limit: int = 30, offset: int = 0) -> tuple[int, list[Hit]]:
    """(total number of hits, the hits from `offset`, at most `limit`)."""
    lexicon = lexicon or default_lexicon()
    rank = ranks(lexicon)
    key = lookup_key(query.strip())
    if key and not set(key) <= _CYRILLIC:
        return 0, []

    def keep(lx: Lexeme) -> bool:
        return pos is None or _pos_group(lx) == pos

    def order(lx: Lexeme) -> tuple:
        return (rank.get(lx.id, 10**9), lx.id)

    hits: list[Hit] = []
    seen: set[str] = set()
    if key:
        for lexeme, _ in lexicon.entries(key):
            if lexeme.id not in seen and keep(lexeme):
                seen.add(lexeme.id)
                hits.append(Hit(lexeme, rank.get(lexeme.id), "form"))
        hits.sort(key=lambda h: order(h.lexeme))
        prefixed = [lx for lx in lexicon.lexemes.values()
                    if lx.id not in seen and keep(lx)
                    and (lookup_key(lx.lemma).startswith(key) or lookup_key(lx.headword).startswith(key))]
        hits += [Hit(lx, rank.get(lx.id), "prefix") for lx in sorted(prefixed, key=order)]
    else:
        everything = sorted((lx for lx in lexicon.lexemes.values() if keep(lx)), key=order)
        hits = [Hit(lx, rank.get(lx.id), "browse") for lx in everything]
    return len(hits), hits[offset:offset + limit]
