"""A morphological tag: a set of grammemes such as "NOUN,inan,femn sing,gent".

OpenCorpora writes the lexeme's fixed grammemes before the space and the form's
own grammemes after it. Tag keeps both parts and gives typed access to each
category.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property

from .grammemes import CATEGORIES, GRAMMEMES, describe


@dataclass(frozen=True)
class Tag:
    text: str

    @cached_property
    def lexical(self) -> tuple[str, ...]:
        """Grammemes shared by every form of the lexeme (part of speech, gender of a noun, …)."""
        head = self.text.split(" ", 1)[0]
        return tuple(g for g in head.split(",") if g)

    @cached_property
    def inflectional(self) -> tuple[str, ...]:
        """Grammemes of this particular form (case, number, tense, …)."""
        parts = self.text.split(" ", 1)
        return tuple(g for g in parts[1].split(",") if g) if len(parts) > 1 else ()

    @cached_property
    def grammemes(self) -> frozenset[str]:
        return frozenset(self.lexical + self.inflectional)

    def __contains__(self, code: str) -> bool:
        return code in self.grammemes

    def _one(self, category: str) -> str | None:
        found = [g for g in self.lexical + self.inflectional
                 if (info := GRAMMEMES.get(g)) is not None and info.category == category]
        return found[0] if found else None

    @property
    def pos(self) -> str | None:
        return self.lexical[0] if self.lexical else None

    @property
    def case(self) -> str | None:
        return self._one("case")

    @property
    def number(self) -> str | None:
        return next((g for g in ("sing", "plur") if g in self.grammemes), None)

    @property
    def gender(self) -> str | None:
        return self._one("gender")

    @property
    def animacy(self) -> str | None:
        return self._one("animacy")

    @property
    def aspect(self) -> str | None:
        return self._one("aspect")

    @property
    def tense(self) -> str | None:
        return self._one("tense")

    @property
    def person(self) -> str | None:
        return self._one("person")

    @property
    def mood(self) -> str | None:
        return self._one("mood")

    def by_category(self) -> list[tuple[str, str]]:
        """(category, code) pairs in a stable, readable order; unknown codes go last."""
        order = {c: i for i, c in enumerate(CATEGORIES)}
        known = [(GRAMMEMES[g].category, g) for g in self.lexical + self.inflectional if g in GRAMMEMES]
        unknown = [("other", g) for g in self.lexical + self.inflectional if g not in GRAMMEMES]
        return sorted(dict.fromkeys(known), key=lambda cg: order.get(cg[0], 99)) + unknown

    def describe(self, lang: str = "uz") -> str:
        """Readable description, e.g. "ot · jonsiz · ayol jinsi · birlik · qaratqich kelishigi"."""
        return " · ".join(describe(code, lang) for _, code in self.by_category())

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "grammemes": [code for _, code in self.by_category()],
            "pos": self.pos,
            "case": self.case,
            "number": self.number,
            "gender": self.gender,
            "animacy": self.animacy,
            "aspect": self.aspect,
            "tense": self.tense,
            "person": self.person,
            "mood": self.mood,
        }
