"""Dictionary search (engine/search.py) and the bridge's "search" op."""

from tilsim_core.bridge import dispatch
from tilsim_core.engine import default_lexicon
from tilsim_core.engine.search import ranks, search


def lemmas(hits):
    return [h.lexeme.headword for h in hits]


def test_a_form_finds_its_lexeme_first():
    total, hits = search("книги")
    assert hits[0].lexeme.lemma == "книга" and hits[0].match == "form"


def test_a_beginning_finds_words_by_frequency():
    total, hits = search("кни", limit=50)
    assert "книга" in lemmas(hits) and all(h.match == "prefix" for h in hits)
    ranked = [h.rank for h in hits if h.rank is not None]
    assert ranked == sorted(ranked)


def test_yo_and_case_do_not_matter():
    assert lemmas(search("ЁЛКА")[1]) == lemmas(search("елка")[1])
    assert "ребёнок" in lemmas(search("ребен")[1])


def test_browse_lists_the_most_frequent_words_with_paging():
    total, first = search("", limit=10)
    _, second = search("", limit=10, offset=10)
    assert total == len(default_lexicon().lexemes)
    assert [h.rank for h in first] == list(range(1, 11)) and second[0].rank == 11


def test_part_of_speech_filter():
    _, hits = search("", pos="VERB", limit=20)
    assert hits and all(h.lexeme.pos == "INFN" for h in hits)


def test_latin_query_finds_nothing_here():
    assert search("kitob") == (0, [])


def test_ranks_are_unique_and_start_at_one():
    values = sorted(ranks(default_lexicon()).values())
    assert values[0] == 1 and values == list(range(1, len(values) + 1))


def test_search_op():
    result = dispatch("search", {"query": "дом", "lang": "en", "limit": 5})
    first = result["items"][0]
    assert first["lemma"] == "дом" and first["rank"] and first["description"].startswith("noun")
