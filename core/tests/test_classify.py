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
    "numerals": "numeral",
    "adverbs": "adverb",
    "predicatives": "predicative",
    "prepositions": "preposition",
    "conjunctions": "conjunction",
    "particles": "particle",
    "interjections": "interjection",
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


def test_every_word_in_the_lexicon_gets_a_class():
    # A class the engine cannot tell is None; for the bundled lexicon every word must have one, so the
    # dictionary never shows "no rules yet" (a closed-class list that misses a pronoun would show up here).
    for lexeme in default_lexicon().lexemes.values():
        profile = classify(lexeme)
        assert profile is not None and profile.category is not None, (lexeme.lemma, lexeme.pos)


def test_a_preposition_explains_each_case_in_the_readers_language():
    [lexeme] = [lx for lx in default_lexicon().by_lemma("в") if lx.pos == "PREP"]
    findings = classify(lexeme).to_dict("uz")["findings"]
    assert findings[0] == {"rule": "prep.accs", "detail": "в школу, в среду",
                           "note": "qayerga? (ichiga); qachon? (kun, soat)"}
    assert "note" not in classify(lexeme).to_dict()["findings"][0]
