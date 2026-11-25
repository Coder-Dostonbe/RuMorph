import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import build  # noqa: E402

WORDS = {"книга", "кто-то", "ёж", "дом"}
KEYS = build.index(WORDS)


def test_lingua_libre_names():
    assert build.parse_ll("LL-Q7737 (rus)-Infovarius-книга.wav", KEYS) == ("Infovarius", "книга")
    # A word with a hyphen, a speaker with a hyphen.
    assert build.parse_ll("LL-Q7737 (rus)-Infovarius-кто-то.wav", KEYS) == ("Infovarius", "кто-то")
    assert build.parse_ll("LL-Q7737 (rus)-Anna-Maria-дом.ogg", KEYS) == ("Anna-Maria", "дом")
    # Stress mark and capital letter in the file name.
    assert build.parse_ll("LL-Q7737 (rus)-X-Кни́га.wav", KEYS) == ("X", "книга")
    # A file without ё stands for the word with ё.
    assert build.parse_ll("LL-Q7737 (rus)-X-еж.wav", KEYS) == ("X", "ёж")
    assert build.parse_ll("LL-Q7737 (rus)-X-стол.wav", KEYS) is None
    # A compound word is not one of its parts.
    assert build.parse_ll("LL-Q7737 (rus)-Cinemantique-ковид-дом.wav", KEYS) is None
    assert build.parse_ll("LL-Q7737 (rus)-Lvova--дом.wav", KEYS) is None
    assert build.parse_ll("LL-Q7737 (rus)-X-книга.txt", KEYS) is None
    assert build.parse_ll("LL-Q150 (fra)-X-книга.wav", KEYS) is None


def test_old_ru_names():
    assert build.parse_ru("Ru-книга.ogg", KEYS) == "книга"
    assert build.parse_ru("Ru-стол.ogg", KEYS) is None
    assert build.parse_ru("En-книга.ogg", KEYS) is None


def test_licenses():
    assert build.license_code("CC BY-SA 4.0") == "CC BY-SA 4.0"
    assert build.license_code("CC-BY-SA-3.0") == "CC BY-SA 3.0"
    assert build.license_code("CC BY 2.5") == "CC BY 2.5"
    assert build.license_code("CC BY 2.0 fr") == "CC BY 2.0 FR"
    assert build.license_base("CC BY 2.0 FR") == "CC BY 2.0"
    assert build.license_code("CC0") == "CC0"
    assert build.license_code("Public domain") == "Public domain"
    assert build.license_code("CC BY-NC-SA 3.0") is None
    assert build.license_code("GFDL") is None
    assert build.license_code("") is None


def test_credit():
    assert build.credit("Tatiana Kerbush", {"Artist": {"value": "Speaker: Tatiana Kerbush Recorder: Tatiana Kerbush"}}) == "Tatiana Kerbush"
    shtooka = {"Credit": {"value": "Audio sample provided by The Shtooka Project."}}
    assert build.credit("Ru", shtooka) == "The Shtooka Project"
    assert build.credit("Ru", {"Artist": {"value": "<a href='x'>1640max</a>"}, **shtooka}) == "1640max"
    assert build.credit("Ru", {}) == ""


def test_author_html_is_stripped():
    assert build.plain_text('<a href="//commons.wikimedia.org/wiki/User:Infovarius">Infovarius</a>') == "Infovarius"


def test_upload_paths():
    url = "https://upload.wikimedia.org/wikipedia/commons/transcoded/a/ab/LL-Q7737_(rus)-X-%D0%B4%D0%BE%D0%BC.wav/LL-Q7737_(rus)-X-%D0%B4%D0%BE%D0%BC.wav.mp3"
    assert build.upload_path(url) == "transcoded/a/ab/LL-Q7737_(rus)-X-дом.wav/LL-Q7737_(rus)-X-дом.wav.mp3"
    assert build.upload_path("https://upload.wikimedia.org/wikipedia/commons/3/3f/Ru-дом.ogg") == "3/3f/Ru-дом.ogg"
    assert build.upload_path("https://example.org/a/ab/x.ogg") is None
    assert build.upload_path("https://upload.wikimedia.org/wikipedia/commons/../../x") is None


def test_best_path_prefers_mp3_transcode():
    item = {
        "mime": "audio/wav",
        "url": "https://upload.wikimedia.org/wikipedia/commons/a/ab/X.wav",
        "derivatives": [
            {"src": "https://upload.wikimedia.org/wikipedia/commons/transcoded/a/ab/X.wav/X.wav.ogg", "type": "audio/ogg; codecs=\"vorbis\""},
            {"src": "https://upload.wikimedia.org/wikipedia/commons/transcoded/a/ab/X.wav/X.wav.mp3", "type": "audio/mpeg"},
        ],
    }
    assert build.best_path(item) == "transcoded/a/ab/X.wav/X.wav.mp3"
    assert build.best_path({"mime": "audio/wav", "url": item["url"]}) == "a/ab/X.wav"
    assert build.best_path({"mime": "video/mp4", "url": item["url"]}) is None


def test_the_speaker_with_most_words_wins():
    chosen = build.choose({
        "книга": [("Rare", "File:a"), ("Main", "File:b")],
        "дом": [("Main", "File:c")],
        "кто-то": [("Main", "File:e")],
        "ёж": [("Rare", "File:d")],
    })
    assert chosen["книга"] == ("Main", "File:b")
    assert chosen["ёж"] == ("Rare", "File:d")


def entry(**changes):
    return {"file": "LL-Q7737 (rus)-X-дом.wav", "path": "a/ab/X.wav", "author": "X", "license": "CC BY-SA 4.0", **changes}


def test_validate():
    ok = {"format": build.FORMAT, "version": build.VERSION, "words": {"дом": entry()}}
    build.validate(ok, WORDS)
    for bad in (
        {"words": {"стол": entry()}},
        {"words": {"дом": entry(license="CC BY-NC 4.0")}},
        {"words": {"дом": entry(path="../x")}},
        {"words": {"дом": entry(author="")}},
    ):
        with pytest.raises(build.BuildError):
            build.validate({**ok, **bad}, WORDS)
    with pytest.raises(build.BuildError):
        build.validate({**ok, "words": {"замок": entry()}}, WORDS | {"замок"})
