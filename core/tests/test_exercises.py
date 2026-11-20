"""Generated exercises (tilsim_core/exercises.py): every question has exactly one right answer,
and that answer is what the dictionary says."""

import pytest

from tilsim_core.bridge import dispatch
from tilsim_core.engine import analyze_after, default_lexicon
from tilsim_core.exercises import KINDS, generate

LEX = default_lexicon()
SEEDS = range(8)


def forms_with(lexeme_id, *grammemes):
    return {f.text for f in LEX.lexemes[lexeme_id].find(*grammemes)}


@pytest.mark.parametrize("seed", SEEDS)
def test_case_form_questions(seed):
    qs = generate("case_form", 15, seed)
    assert len(qs) == 15
    for q in qs:
        right = q.options[q.answer]
        assert right in forms_with(q.lexeme, "NOUN", *q.prompt["grammemes"])
        assert all(o not in forms_with(q.lexeme, *q.prompt["grammemes"]) for i, o in enumerate(q.options) if i != q.answer)
        assert len(set(q.options)) == 4


@pytest.mark.parametrize("seed", SEEDS)
def test_conjugation_questions(seed):
    for q in generate("conjugation", 15, seed):
        g = q.prompt["grammemes"]
        assert q.options[q.answer] in forms_with(q.lexeme, "VERB", "indc", *g)
        assert all(o not in forms_with(q.lexeme, "VERB", "indc", *g) for i, o in enumerate(q.options) if i != q.answer)


@pytest.mark.parametrize("seed", SEEDS)
def test_preposition_questions_agree_with_the_phrase_analysis(seed):
    for q in generate("preposition", 15, seed):
        prep = q.prompt["preposition"]
        right = q.options[q.answer]
        result = analyze_after(prep, right)
        assert result.status in ("ok", "ambiguous") and q.lexeme in {r.reading.lexeme.id for r in result.readings}, (prep, right)
        for i, o in enumerate(q.options):
            if i != q.answer:
                result = analyze_after(prep, o)
                assert result.status == "error" or q.lexeme not in {r.reading.lexeme.id for r in result.readings}, (prep, o)


def test_o_becomes_ob_before_a_vowel():
    for seed in range(40):
        for q in generate("preposition", 20, seed):
            if q.prompt["preposition"] in ("о", "об"):
                right = q.options[q.answer]
                assert (q.prompt["preposition"] == "об") == (right[0] in "аоуэи"), right


@pytest.mark.parametrize("kind", ["gender", "aspect"])
def test_closed_choice_questions(kind):
    for q in generate(kind, 20, 3):
        tag = LEX.lexemes[q.lexeme].lemma_tag
        assert q.options[q.answer] in tag
        assert sum(o in tag for o in q.options) == 1


def test_seed_repeats_the_test():
    assert [q.to_dict() for q in generate("case_form", 10, 42)] == [q.to_dict() for q in generate("case_form", 10, 42)]


def test_translation_needs_four_distinct_translations():
    vocab = [{"lexeme_id": f"w{i}", "lemma": f"слово{i}", "translation": t}
             for i, t in enumerate(["kitob", "uy", "suv", "non", "kitob"])]
    qs = generate("translation", 10, 1, vocabulary=vocab)
    assert qs and all(q.options[q.answer] == next(v["translation"] for v in vocab if v["lexeme_id"] == q.lexeme) for q in qs)
    assert all(len(set(q.options)) == 4 for q in qs)
    assert generate("translation", 10, 1, vocabulary=vocab[:3]) == []


def test_exercises_op():
    result = dispatch("exercises", {"kind": "gender", "count": 5, "seed": 1, "max_rank": 500})
    assert len(result) == 5 and {q["kind"] for q in result} == {"gender"}
    with pytest.raises(Exception):
        dispatch("exercises", {"kind": "nope", "count": 5, "seed": 1})


def test_every_kind_is_listed():
    assert set(KINDS) == {"case_form", "conjugation", "gender", "preposition", "aspect", "translation"}
