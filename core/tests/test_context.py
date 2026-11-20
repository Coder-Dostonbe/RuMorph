"""A word after a preposition (engine/context.py) and the government data (engine/prepositions.py)."""

import json

import pytest

from tilsim_core.engine import AMBIGUOUS, ERROR, OK, analyze_after, default_lexicon
from tilsim_core.engine.prepositions import PREPOSITIONS


def run(prep, word):
    return analyze_after(prep, word)


def cases(result):
    return [(r.reading.form.text, r.government.case) for r in result.readings]


@pytest.mark.parametrize(("prep", "word", "status", "expected"), [
    ("без", "книги", OK, [("книги", "gent")]),          # книги alone: gen. sg. or nom./acc. pl.
    ("о", "книге", OK, [("книге", "loct")]),            # книге alone: dative or prepositional
    ("с", "другом", OK, [("другом", "ablt")]),
    ("с", "книги", OK, [("книги", "gent")]),
    ("в", "школу", OK, [("школу", "accs")]),
    ("в", "школе", OK, [("школе", "loct")]),
    ("в", "лесу", OK, [("лесу", "loct")]),              # second locative counts as the prepositional
    ("на", "стол", OK, [("стол", "accs")]),
    ("за", "домом", OK, [("домом", "ablt")]),
    ("по", "улице", OK, [("улице", "datv")]),           # not also the set-phrase "по + prepositional"
    ("во", "время", OK, [("время", "accs")]),            # во is в before some consonant clusters
    ("со", "мной", OK, [("мной", "ablt")]),
])
def test_preposition_narrows_the_readings(prep, word, status, expected):
    result = run(prep, word)
    assert result.status == status, result.to_dict("en")
    assert sorted(set(cases(result))) == expected


def test_two_meanings_stay_ambiguous():
    # метро is indeclinable: after в it can be the accusative (into) or the prepositional (in).
    result = run("в", "метро")
    assert result.status == AMBIGUOUS
    assert {g for _, g in cases(result)} == {"accs", "loct"}


def test_wrong_case_is_an_error_with_the_right_forms():
    result = run("в", "школа")
    assert result.status == ERROR and result.errors[0].code == "wrong_case_after_preposition"
    assert result.suggestions == ["в школу", "в школе"]
    assert "винительный" in result.to_dict("ru")["errors"][0]["message"]


def test_pronoun_after_a_preposition_needs_n():
    result = run("к", "ему")
    assert result.status == ERROR and [e.code for e in result.errors] == ["needs_n_form"]
    assert result.suggestions == ["к нему"]
    # его / её / их are also possessives, which never take н-: say so.
    result = run("у", "его")
    assert [e.code for e in result.errors] == ["needs_n_form", "possessive_without_n"]
    assert result.suggestions == ["у него"]
    assert run("у", "него").status in (OK, AMBIGUOUS)        # он / оно


def test_rare_construction_is_kept_with_a_note_when_it_is_the_only_one():
    result = run("между", "двух")
    assert result.status == OK and result.readings[0].government.rare
    assert "между двух огней" in result.to_dict("uz")["readings"][0]["notes"][-1]


@pytest.mark.parametrize(("prep", "word", "code"), [
    ("в", "читать", "no_case_after_preposition"),
    ("стол", "книга", "not_a_preposition"),
    ("в", "абвгд", "unknown_word"),
    ("в", "", "empty"),
])
def test_errors(prep, word, code):
    result = run(prep, word)
    assert result.status == ERROR and result.errors[0].code == code


def test_every_preposition_in_the_lexicon_has_government_data():
    lexicon = default_lexicon()
    in_lexicon = {lx.lemma for lx in lexicon.lexemes.values() if lx.pos == "PREP"}
    assert in_lexicon <= set(PREPOSITIONS)
    for lemma, governs in PREPOSITIONS.items():
        assert governs and len({g.case for g in governs}) == len(governs), lemma
        for g in governs:
            assert g.uz and g.ru and g.en and g.example, (lemma, g.case)


@pytest.mark.parametrize("lang", ["uz", "ru", "en"])
def test_phrase_result_is_json_in_every_language(lang):
    for prep, word in (("в", "школу"), ("у", "его"), ("в", "школа"), ("по", "колену")):
        json.dumps(run(prep, word).to_dict(lang), ensure_ascii=False)
