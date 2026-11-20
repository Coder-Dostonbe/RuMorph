"""The grammar catalog: which words of the lexicon each rule explains.

Every lexeme is classified once (classify.py) and indexed by the rules its
profile names, its class and each finding, with the finding's own example
(день → дня). The grammar module shows a rule with the most frequent words it
applies to, so its examples are real words of the dictionary, not a fixed list.
"""

from __future__ import annotations

from .classify import classify
from .lexicon import Lexeme, Lexicon, default_lexicon
from .search import ranks

# Display order of the rule groups (by rule id prefix).
GROUPS = ("noun", "adj", "pron", "num", "verb", "spelling")


def rule_index(lexicon: Lexicon | None = None) -> dict[str, list[tuple[Lexeme, str]]]:
    """rule id → [(lexeme, this word's example)], most frequent words first. Built once."""
    lexicon = lexicon or default_lexicon()
    cached = getattr(lexicon, "_rule_index", None)
    if cached is not None:
        return cached
    rank = ranks(lexicon)
    index: dict[str, list[tuple[Lexeme, str]]] = {}
    for lexeme in lexicon.lexemes.values():
        had_forms = "forms" in lexeme.__dict__
        profile = classify(lexeme)
        if not had_forms:
            # Classifying built every form of every word; let them go again (they are rebuilt on use).
            lexeme.__dict__.pop("forms", None)
        if profile is None:
            continue
        if profile.category:
            index.setdefault(profile.category, []).append((lexeme, lexeme.headword))
        for finding in profile.findings:
            index.setdefault(finding.rule_id, []).append((lexeme, finding.detail))
    for entries in index.values():
        entries.sort(key=lambda e: (rank.get(e[0].id, 10**9), e[0].id))
    lexicon._rule_index = index        # type: ignore[attr-defined]
    return index


def group_of(rule_id: str) -> str | None:
    head = rule_id.split(".", 1)[0]
    return head if head in GROUPS else None
