"""Classification against hand-checked corpora (tests/corpus/*.json).

Each corpus entry gives a lemma, its class (declension, stem type or kind of
pronoun) and every finding it must have. Findings not listed must not appear,
so a change that starts reporting something new (or stops) fails here. Every
rule in the registry must be covered by a corpus or be listed as covered
elsewhere.
"""

import json
from pathlib import Path

import pytest

from tilsim_core.engine import RULES, classify, default_lexicon

CORPUS_DIR = Path(__file__).parent / "corpus"
CORPORA = {
    # corpus file → the profile kind its lemmas must get
    "nouns": "noun",
    "adjectives": "adjective",
    "pronouns": "pronoun",
    "verbs": "verb",
}
ENTRIES = [(name, entry) for name in CORPORA
           for entry in json.loads((CORPUS_DIR / f"{name}.json").read_text(encoding="utf-8"))["entries"]]
# Rules that are not about classification; tested in test_engine.py (the compound future is a table cell).
COVERED_ELSEWHERE = {"lexicon.form", "lexicon.rare_form", "verb.future_compound"}


def profiles(lemma, kind):
    found = [classify(lx) for lx in default_lexicon().by_lemma(lemma)]
    found = [p for p in found if p is not None and p.kind == kind]
    assert found, f"{lemma} is not in the lexicon as a {kind}"
    return found


@pytest.mark.parametrize(("corpus", "entry"), ENTRIES, ids=lambda v: v if isinstance(v, str) else v["lemma"])
def test_corpus(corpus, entry):
    results = profiles(entry["lemma"], CORPORA[corpus])
    expected = {(f["rule"], f["detail"]) for f in entry["findings"]}
    # Homonymous lexemes (кошка animal / tool) must agree with the entry; at least one must match exactly.
    matches = [p for p in results
               if p.category == entry["category"] and {(f.rule_id, f.detail) for f in p.findings} == expected]
    assert matches, [p.to_dict() for p in results]


def test_every_rule_is_covered():
    used = {e["category"] for _, e in ENTRIES} | {f["rule"] for _, e in ENTRIES for f in e["findings"]}
    assert set(RULES) - used - COVERED_ELSEWHERE == set()


def test_corpus_rules_exist():
    for _, entry in ENTRIES:
        assert entry["category"] in RULES, entry
        assert all(f["rule"] in RULES for f in entry["findings"]), entry


def test_every_rule_has_three_languages_and_an_example():
    for rule in RULES.values():
        assert rule.name_uz and rule.name_ru and rule.name_en, rule.id
        assert rule.explanation_uz and rule.explanation_ru and rule.explanation_en, rule.id
        assert rule.review_status == "pending_specialist_review", rule.id


def test_every_pronoun_and_adjective_in_the_lexicon_gets_a_profile():
    # A closed-class list that misses a lexicon pronoun would silently give category None.
    # "один" is a numeral (OpenCorpora tags it as a pronominal adjective); step 2.6 classifies it.
    pending = {"один"}
    for lexeme in default_lexicon().lexemes.values():
        profile = classify(lexeme)
        if lexeme.pos in ("NPRO", "ADJF", "ADJS") and lexeme.lemma not in pending:
            assert profile is not None and profile.category is not None, lexeme.lemma


def test_every_verb_in_the_lexicon_gets_a_conjugation():
    for lexeme in default_lexicon().lexemes.values():
        if lexeme.pos == "INFN":
            assert classify(lexeme).category is not None, lexeme.lemma
