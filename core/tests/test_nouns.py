"""Noun classification against a hand-checked corpus (tests/corpus/nouns.json).

Each corpus entry gives a lemma, its declension rule and the findings it must
have. Findings not listed must not appear, so a change that starts reporting
something new (or stops) fails here. Every rule in the registry must be covered
by the corpus or be explicitly listed as covered elsewhere.
"""

import json
from pathlib import Path

import pytest

from tilsim_core.engine import RULES, classify_noun, default_lexicon

CORPUS = json.loads((Path(__file__).parent / "corpus" / "nouns.json").read_text(encoding="utf-8"))
# Rules that are not about nouns' classification; tested in test_engine.py.
COVERED_ELSEWHERE = {"lexicon.form", "lexicon.rare_form"}


def profiles(lemma):
    lexemes = [lx for lx in default_lexicon().by_lemma(lemma) if lx.pos == "NOUN"]
    assert lexemes, f"{lemma} is not in the lexicon"
    return [classify_noun(lx) for lx in lexemes]


@pytest.mark.parametrize("entry", CORPUS["entries"], ids=lambda e: e["lemma"])
def test_noun_corpus(entry):
    results = profiles(entry["lemma"])
    expected = {(f["rule"], f["detail"]) for f in entry["findings"]}
    # Homonymous lexemes (кошка animal / tool) must agree with the entry; at least one must match exactly.
    matches = [p for p in results
               if p.declension == entry["declension"] and {(f.rule_id, f.detail) for f in p.findings} == expected]
    assert matches, [p.to_dict() for p in results]


def test_every_rule_is_covered():
    used = {e["declension"] for e in CORPUS["entries"]} | {f["rule"] for e in CORPUS["entries"] for f in e["findings"]}
    assert set(RULES) - used - COVERED_ELSEWHERE == set()


def test_every_rule_has_three_languages_and_an_example():
    for rule in RULES.values():
        assert rule.name_uz and rule.name_ru and rule.name_en, rule.id
        assert rule.explanation_uz and rule.explanation_ru and rule.explanation_en, rule.id
        assert rule.review_status == "pending_specialist_review", rule.id
