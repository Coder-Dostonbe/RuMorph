"""Reading preparation (tilsim_core/reading.py)."""

import pytest

from tilsim_core.bridge import dispatch
from tilsim_core.reading import MAX_TEXT, prepare


def test_words_are_linked_to_the_dictionary():
    text = "Мама читает книгу. Кнога лежит."
    result = prepare(text)
    words = [text[t["start"]:t["end"]] for t in result["tokens"]]
    assert words == ["Мама", "читает", "книгу", "Кнога", "лежит"]
    by_word = dict(zip(words, result["tokens"]))
    assert by_word["книгу"]["lexemes"] == ["книга|NOUN,inan,femn"] and by_word["книгу"]["known"]
    assert not by_word["Кнога"]["known"] and by_word["Кнога"]["lexemes"] == []


def test_difficulty_is_measured():
    result = prepare("Мама читает книгу. Кнога лежит.")
    assert result["words"] == 5 and result["unknown"] == 20.0
    assert result["coverage"]["3000"] == 80.0
    assert result["coverage"]["500"] <= result["coverage"]["1000"] <= result["coverage"]["3000"]


def test_empty_and_latin_text():
    assert prepare("Hello, world!")["words"] == 0


def test_limit_and_op():
    with pytest.raises(ValueError):
        prepare("а" * (MAX_TEXT + 1))
    assert dispatch("reading", {"text": "Я дома."})["words"] == 2
