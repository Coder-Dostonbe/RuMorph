"""The lexicon: lexemes with their full inflection paradigms.

Loaded from a package file (data/ru_core.json, see tools/lexicon). A lexeme is a
stem plus a paradigm; each paradigm row gives a prefix, a suffix and a tag, and
the word form is prefix + stem + suffix. Row 0 is the lemma.

Forms are indexed by their lookup key (lower case, ё folded to е), so analysis
is a dictionary lookup.

A lexeme's id is built from its lemma and the grammemes that hold for the
whole word ("книга|NOUN,inan,femn"), not from its position in the file, so the
user's cards and notes keep pointing at the same word when the lexicon grows.
Two lexemes that would get the same id are told apart by "|2", "|3", …. Several packages can be merged (the core list now; the
full dictionary and the user's own words later).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cached_property
from importlib import resources

from .normalize import lookup_key
from .tag import Tag


@dataclass(frozen=True)
class WordForm:
    text: str
    tag: Tag
    index: int          # position in the paradigm


@dataclass(frozen=True)
class Lexeme:
    id: str             # "<lemma>|<lexical grammemes>", stable across lexicon versions
    stem: str
    rows: tuple[tuple[str, str, Tag], ...]   # (prefix, suffix, tag)
    source: str
    freq: float | None = None   # Zipf frequency (wordfreq), None when unknown

    @cached_property
    def forms(self) -> tuple[WordForm, ...]:
        return tuple(WordForm(prefix + self.stem + suffix, tag, i)
                     for i, (prefix, suffix, tag) in enumerate(self.rows))

    @property
    def lemma(self) -> str:
        return self.forms[0].text

    @property
    def headword(self) -> str:
        """The form to show as the dictionary entry. Usually the lemma; for a noun whose singular
        forms are all rare (OpenCorpora: деньга, Infr) the nominative plural (деньги)."""
        if self.pos == "NOUN" and "Infr" in self.lemma_tag:
            plural = [f for f in self.find("plur", "nomn") if "Infr" not in f.tag]
            if plural:
                return plural[0].text
        return self.lemma

    @property
    def lemma_tag(self) -> Tag:
        return self.forms[0].tag

    @property
    def pos(self) -> str | None:
        return self.lemma_tag.pos

    def find(self, *grammemes: str, exclude: tuple[str, ...] = ()) -> list[WordForm]:
        """Forms whose tag has every grammeme given and none of `exclude`."""
        return [f for f in self.forms
                if all(g in f.tag for g in grammemes) and not any(g in f.tag for g in exclude)]

    def form(self, *grammemes: str, exclude: tuple[str, ...] = ()) -> WordForm | None:
        found = self.find(*grammemes, exclude=exclude)
        return found[0] if found else None


class LexiconError(Exception):
    pass


_ROWS = 1024        # more than any paradigm has forms (verbs with all participles: ~250)


class Lexicon:
    def __init__(self) -> None:
        self.lexemes: dict[str, Lexeme] = {}
        self.packages: list[dict] = []
        self._order: list[Lexeme] = []
        # lookup key → packed entries (lexeme number * _ROWS + form index): one int when the key
        # has one reading, a tuple when it has several. Packed this way the index of a few
        # thousand lexemes stays small, which keeps the app's memory snapshot small.
        self._index: dict[str, int | tuple[int, ...]] | None = None

    @classmethod
    def from_package(cls, data: dict) -> Lexicon:
        lexicon = cls()
        lexicon.add_package(data)
        return lexicon

    def add_package(self, data: dict) -> None:
        try:
            name = str(data["package"])
            tags = [Tag(t) for t in data["tags"]]
            paradigms = [tuple((str(p), str(s), tags[t]) for p, s, t in rows) for rows in data["paradigms"]]
            freqs = data.get("freq") or [None] * len(data["lexemes"])
            if len(freqs) != len(data["lexemes"]):
                raise LexiconError("'freq' and 'lexemes' differ in length")
            for (stem, paradigm), freq in zip(data["lexemes"], freqs):
                rows = paradigms[paradigm]
                if not rows:
                    raise LexiconError(f"empty paradigm for {stem!r}")
                prefix, suffix, tag = rows[0]
                base = f"{prefix}{stem}{suffix}|{','.join(tag.lexical)}"
                lexeme_id, n = base, 1
                while lexeme_id in self.lexemes:
                    n += 1
                    lexeme_id = f"{base}|{n}"
                if len(rows) >= _ROWS:
                    raise LexiconError(f"paradigm of {lexeme_id} has more than {_ROWS - 1} forms")
                lexeme = Lexeme(lexeme_id, str(stem), rows, name, float(freq) if freq is not None else None)
                self.lexemes[lexeme_id] = lexeme
                self._order.append(lexeme)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LexiconError(f"invalid lexicon package: {exc!r}") from exc
        self.packages.append({k: data.get(k) for k in ("package", "version", "description", "source")})
        self._index = None

    @property
    def index(self) -> dict[str, int | tuple[int, ...]]:
        """lookup key → packed entries, built on first use without creating the word forms."""
        if self._index is None:
            index: dict[str, int | tuple[int, ...]] = {}
            for number, lexeme in enumerate(self._order):
                stem = lexeme.stem
                for i, (prefix, suffix, _tag) in enumerate(lexeme.rows):
                    key = lookup_key(prefix + stem + suffix)
                    entry = number * _ROWS + i
                    found = index.get(key)
                    if found is None:
                        index[key] = entry
                    elif isinstance(found, int):
                        index[key] = (found, entry)
                    else:
                        index[key] = found + (entry,)
            self._index = index
        return self._index

    def entries(self, key: str) -> list[tuple[Lexeme, int]]:
        """(lexeme, form index) for every form with this lookup key."""
        found = self.index.get(key)
        if found is None:
            return []
        packed = (found,) if isinstance(found, int) else found
        return [(self._order[e // _ROWS], e % _ROWS) for e in packed]

    def lookup(self, key: str) -> list[tuple[Lexeme, WordForm]]:
        return [(lexeme, lexeme.forms[i]) for lexeme, i in self.entries(key)]

    def by_lemma(self, lemma: str) -> list[Lexeme]:
        key = lookup_key(lemma)
        return [lx for lx in self.lexemes.values() if key in (lookup_key(lx.lemma), lookup_key(lx.headword))]

    def info(self) -> dict:
        return {
            "packages": self.packages,
            "lexemes": len(self.lexemes),
            "forms": sum(len(lx.rows) for lx in self.lexemes.values()),
        }


_default: Lexicon | None = None


def default_lexicon() -> Lexicon:
    """The lexicon bundled with the app (loaded once)."""
    global _default
    if _default is None:
        text = resources.files("tilsim_core.data").joinpath("ru_core.json").read_text(encoding="utf-8")
        _default = Lexicon.from_package(json.loads(text))
    return _default
