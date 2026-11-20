"""Spell and grammar check (tilsim_core/spell.py)."""

import pytest

from tilsim_core.bridge import dispatch
from tilsim_core.spell import MAX_TEXT, check


def issues(text):
    return [(i.level, text[i.start:i.end], i.suggestions) for i in check(text).issues]


def test_correct_text_has_no_issues():
    text = "Я иду в школу. Мы живём в большом доме, и у нас есть сад. Вокруг тишина."
    assert issues(text) == []


def test_wrong_case_after_a_preposition():
    assert issues("Я иду в школа.") == [("grammar", "школа", ["в школу", "в школе"])]


def test_pronoun_needs_n_and_keeps_the_capital():
    result = check("К ему пришёл друг.")
    (issue,) = result.issues
    assert issue.level == "grammar" and issue.suggestions == ["К нему"]
    assert "К ему" == "К ему пришёл друг."[issue.to_dict("uz")["replace_start"]:issue.to_dict("uz")["replace_end"]]


def test_possessive_his_is_not_an_error():
    assert issues("У его брата есть машина.") == []


def test_an_adverb_like_preposition_is_not_checked():
    # вокруг, после, около also stand alone as adverbs.
    assert issues("Вокруг тишина.") == []


def test_unknown_word_is_not_called_an_error():
    (level, word, suggestions), = issues("Кнога лежит.")
    assert level == "unknown" and suggestions[0] == "Книга"


def test_latin_letter_in_a_cyrillic_word_is_an_error():
    assert issues("Книга на столe.") == [("error", "столe", ["столе"])]


def test_uzbek_letters_are_an_error():
    assert issues("Бу китоб қизиқ.")[-1][0] == "error"


def test_yo_note():
    assert issues("Еще одна книга.") == [("note", "Еще", ["Ещё"])]


def test_repeated_word():
    assert ("repeat", "и", []) in issues("Он читал и и писал.")


def test_latin_only_words_are_left_alone():
    assert issues("У меня есть iPhone.") == []


def test_counts():
    result = check("Я читаю книгу кнога.")
    assert result.words == 4 and result.known == 3


def test_limit():
    with pytest.raises(ValueError):
        check("а" * (MAX_TEXT + 1))


def test_spellcheck_op():
    result = dispatch("spellcheck", {"text": "Я иду в школа.", "lang": "en"})
    assert result["issues"][0]["level"] == "grammar" and "accusative" in result["issues"][0]["messages"][0]
