"""The grammar catalog (engine/catalog.py) and its bridge ops."""

from tilsim_core.bridge import dispatch
from tilsim_core.engine import RULES
from tilsim_core.engine.catalog import GROUPS, group_of, rule_index


def test_every_grammar_rule_is_in_a_group():
    assert {group_of(r) for r in RULES if not r.startswith("lexicon.")} == set(GROUPS)


def test_examples_are_real_words_with_their_own_detail():
    index = rule_index()
    fleeting = index["noun.fleeting_vowel"]
    assert ("день", "день → дня") in [(lx.lemma, d) for lx, d in fleeting]
    # Every class rule and most exception rules have words in the dictionary.
    assert index["noun.decl.1"] and index["verb.conj.2"] and index["pron.personal"]


def test_examples_are_ordered_by_frequency():
    freqs = [lx.freq or 0 for lx, _ in rule_index()["noun.decl.2"][:50]]
    assert freqs == sorted(freqs, reverse=True)


def test_grammar_op_counts_words():
    groups = dispatch("grammar", {"lang": "en"})["groups"]
    assert [g["id"] for g in groups] == list(GROUPS)
    nouns = {r["id"]: r for r in groups[0]["rules"]}
    assert nouns["noun.decl.1"]["name"] == "1st declension" and nouns["noun.decl.1"]["words"] > 100


def test_rule_examples_op_pages():
    first = dispatch("rule_examples", {"rule": "verb.conj.1", "limit": 5})
    more = dispatch("rule_examples", {"rule": "verb.conj.1", "limit": 5, "offset": 5})
    assert first["total"] > 100 and len(first["items"]) == 5
    assert {i["id"] for i in first["items"]}.isdisjoint({i["id"] for i in more["items"]})


def test_prepositions_op():
    items = {p["preposition"]: p for p in dispatch("prepositions", {"lang": "uz"})}
    assert [g["case"] for g in items["в"]["governs"]] == ["accs", "loct"]
