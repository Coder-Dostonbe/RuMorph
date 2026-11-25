"""The pronunciation proxy (/v1/audio/...): no database needed."""

import asyncio
from urllib.parse import quote

from conftest import ORIGIN, make_settings

from tilsim_api import audio
from tilsim_api.app import Context, handle
from tilsim_api.http import Request

LL = "LL-Q7737_(rus)-Infovarius-книга.wav"
ORIGINAL = f"a/ab/{LL}"
TRANSCODED = f"transcoded/a/ab/{LL}/{LL}.mp3"


async def no_database():
    raise AssertionError("the audio route must not touch the database")


def call(path, fetch=None, origin=ORIGIN):
    seen = []

    async def fake_fetch(url):
        seen.append(url)
        return fetch(url) if fetch else (200, "audio/mpeg", b"ID3 audio")

    ctx = Context(settings=make_settings(), connect=no_database, fetch_bytes=fake_fetch)
    request = Request(method="GET", url="https://api.test" + path, headers={"origin": origin})
    return asyncio.run(handle(request, ctx)), seen


def test_target_accepts_russian_pronunciations_only():
    assert audio.target("/v1/audio/" + quote(ORIGINAL)) == \
        "https://upload.wikimedia.org/wikipedia/commons/a/ab/LL-Q7737_(rus)-Infovarius-%D0%BA%D0%BD%D0%B8%D0%B3%D0%B0.wav"
    assert audio.target("/v1/audio/" + quote(TRANSCODED)).endswith(".wav.mp3")
    assert audio.target("/v1/audio/3/3f/Ru-" + quote("дом") + ".ogg")
    for bad in (
        "a/ab/LL-Q150_(fra)-X-chat.wav",          # not Russian
        "a/ab/Some_photo.jpg",                    # not a pronunciation
        "a/ab/Ru-x.exe",
        "a/abc/Ru-x.ogg",                         # not a Commons hash path
        "../a/ab/Ru-x.ogg",
        "transcoded/a/ab/Ru-x.ogg/Other.ogg.mp3",  # transcode of another file
        "a/ab/c/Ru-x.ogg",
    ):
        assert audio.target("/v1/audio/" + quote(bad)) is None, bad
    assert audio.target("/v1/translations") is None


def test_serves_the_recording_with_cors_and_cache_headers():
    response, seen = call("/v1/audio/" + quote(TRANSCODED))
    assert response.status == 200
    assert response.body == b"ID3 audio"
    assert response.headers["content-type"] == "audio/mpeg"
    assert "max-age" in response.headers["cache-control"]
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert seen == [audio.target("/v1/audio/" + quote(TRANSCODED))]


def test_other_files_are_not_fetched():
    response, seen = call("/v1/audio/" + quote("a/ab/Some_photo.jpg"))
    assert response.status == 404 and seen == []


def test_upstream_problems():
    response, _ = call("/v1/audio/" + quote(ORIGINAL), fetch=lambda url: (404, "", b""))
    assert response.status == 404
    response, _ = call("/v1/audio/" + quote(ORIGINAL), fetch=lambda url: (200, "text/html", b"<html>"))
    assert response.status == 502 and response.json()["error"]["code"] == "audio_unavailable"
    response, _ = call("/v1/audio/" + quote(ORIGINAL), fetch=lambda url: (200, "audio/wav", b"x" * (audio.MAX_BYTES + 1)))
    assert response.status == 502

    def boom(url):
        raise OSError("network")

    response, _ = call("/v1/audio/" + quote(ORIGINAL), fetch=boom)
    assert response.status == 502


def test_without_a_fetcher_it_says_so():
    ctx = Context(settings=make_settings(), connect=no_database)
    request = Request(method="GET", url="https://api.test/v1/audio/" + quote(ORIGINAL), headers={})
    response = asyncio.run(handle(request, ctx))
    assert response.status == 503
