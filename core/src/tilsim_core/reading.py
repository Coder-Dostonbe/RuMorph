"""A text prepared for reading: its words linked to the dictionary, and how hard it is.

Each Cyrillic word gets its readings' lexemes (most frequent first), so the app
can show a word's analysis on a tap and colour the words the learner already
keeps. The difficulty is measured, not guessed: the share of the text's words
(running words, by their most frequent reading) that are among the 500 / 1000
/ 3000 most frequent words, and the share the dictionary does not know.
"""

from __future__ import annotations

import re

from .engine.analyze import ERROR, analyze
from .engine.lexicon import Lexicon, default_lexicon
from .engine.search import ranks

MAX_TEXT = 50000
_WORD = re.compile(r"[А-Яа-яЁё́]+(?:-[А-Яа-яЁё́]+)*")
BANDS = (500, 1000, 3000)


def prepare(text: str, lexicon: Lexicon | None = None) -> dict:
    if len(text) > MAX_TEXT:
        raise ValueError(f"text longer than {MAX_TEXT} characters")
    lexicon = lexicon or default_lexicon()
    rank = ranks(lexicon)
    cache: dict[str, dict] = {}
    tokens = []
    in_band = dict.fromkeys(BANDS, 0)
    unknown = 0
    lemmas: set[str] = set()
    for match in _WORD.finditer(text):
        word = match.group(0)
        key = word.lower()
        info = cache.get(key)
        if info is None:
            result = analyze(word, lexicon)
            ids = list(dict.fromkeys(r.lexeme.id for r in result.readings))
            info = {"lexemes": ids, "known": result.status != ERROR,
                    "rank": min((rank[i] for i in ids if i in rank), default=None)}
            cache[key] = info
        tokens.append({"start": match.start(), "end": match.end(), **info})
        if not info["known"]:
            unknown += 1
            continue
        lemmas.add(info["lexemes"][0])
        for band in BANDS:
            if info["rank"] is not None and info["rank"] <= band:
                in_band[band] += 1
    total = len(tokens)
    share = (lambda n: round(100 * n / total, 1)) if total else (lambda n: 0.0)
    return {
        "tokens": tokens,
        "words": total,
        "distinct_lemmas": len(lemmas),
        "coverage": {str(b): share(n) for b, n in in_band.items()},
        "unknown": share(unknown),
    }
