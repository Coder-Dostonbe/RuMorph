"""Shared word translations (tilsim_api/translations.py)."""

import pytest
from conftest import device

PASSWORD = "juda-maxfiy-parol"


def register(api, email):
    r = api.call("POST", "/v1/auth/register", {"email": email, "password": PASSWORD, "device": device()})
    assert r.status == 201, r.body
    return r.json()["access_token"]


def entry(lexeme="книга|NOUN,inan,femn", translation="kitob", updated_at="2026-11-20T09:00:00.000Z", deleted_at=None,
          lemma="книга"):
    return {"lexeme_id": lexeme, "lemma": lemma, "translation": translation, "updated_at": updated_at,
            "deleted_at": deleted_at}


def push(api, token, *entries):
    return api.call("POST", "/v1/translations", {"changes": list(entries)}, token=token)


def pull(api, since=0):
    r = api.call("GET", f"/v1/translations?since={since}")
    assert r.status == 200, r.body
    return r.json()


@pytest.fixture
def admin(api):
    return register(api, "doston@example.com")  # the first account is the admin


def test_anyone_can_read_without_an_account(api, admin):
    push(api, admin, entry())
    got = pull(api)
    assert [(e["lexeme_id"], e["translation"]) for e in got["changes"]] == [("книга|NOUN,inan,femn", "kitob")]
    assert got["changes"][0]["updated_at"].startswith("2026-11-20T09:00:00")
    assert got["more"] is False and got["cursor"] > 0
    assert pull(api, got["cursor"])["changes"] == []


def test_only_admins_write(api, admin):
    learner = register(api, "mehmon@example.com")
    r = push(api, learner, entry())
    assert r.status == 403 and r.json()["error"]["code"] == "not_admin"
    assert api.call("POST", "/v1/translations", {"changes": [entry()]}).status == 401
    assert pull(api)["changes"] == []


def test_later_change_wins(api, admin):
    push(api, admin, entry(translation="kitob"))
    r = push(api, admin, entry(translation="eski", updated_at="2026-11-19T09:00:00Z")).json()
    assert r["accepted"] == [] and r["conflicts"][0]["translation"] == "kitob"
    r = push(api, admin, entry(translation="kitob, daftar", updated_at="2026-11-21T09:00:00Z")).json()
    assert r["accepted"] == ["книга|NOUN,inan,femn"]
    first = pull(api)
    assert [e["translation"] for e in first["changes"]] == ["kitob, daftar"]


def test_removal_reaches_devices(api, admin):
    push(api, admin, entry())
    cursor = pull(api)["cursor"]
    gone = entry(updated_at="2026-11-21T09:00:00Z", deleted_at="2026-11-21T09:00:00Z")
    assert push(api, admin, gone).json()["accepted"]
    (change,) = pull(api, cursor)["changes"]
    assert change["deleted_at"] is not None


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ({"translation": ""}, "invalid_translation"),
        ({"translation": "x" * 201}, "invalid_translation"),
        ({"translation": " kitob "}, "invalid_translation"),
        ({"lemma": ""}, "invalid_lemma"),
        ({"lexeme_id": ""}, "invalid_lexeme_id"),
        ({"updated_at": "kecha"}, "invalid_updated_at"),
        ({"updated_at": "2026-11-25T09:00:00Z"}, "invalid_updated_at"),  # a day ahead of the server clock
        ({"deleted_at": "x"}, "invalid_deleted_at"),
    ],
)
def test_bad_entries_are_refused_one_by_one(api, admin, change, code):
    good = entry(lexeme="дом|NOUN,inan,masc", lemma="дом", translation="uy")
    r = push(api, admin, {**entry(), **change}, good).json()
    assert [x["code"] for x in r["rejected"]] == [code]
    assert r["accepted"] == ["дом|NOUN,inan,masc"]


def test_removed_entry_may_have_empty_text(api, admin):
    r = push(api, admin, entry(translation="", deleted_at="2026-11-20T09:00:00Z")).json()
    assert r["accepted"]


def test_limits(api, admin):
    many = [entry(lexeme=str(i)) for i in range(201)]
    assert push(api, admin, *many).json()["error"]["code"] == "too_many_changes"
    assert api.call("GET", "/v1/translations?since=x").json()["error"]["code"] == "invalid_since"


def test_pull_pages(api, admin, monkeypatch):
    from tilsim_api import translations

    monkeypatch.setattr(translations, "PULL_LIMIT", 2)
    push(api, admin, *[entry(lexeme=f"w{i}", lemma=f"w{i}") for i in range(5)])
    seen, cursor, more = [], 0, True
    while more:
        page = pull(api, cursor)
        seen += [e["lexeme_id"] for e in page["changes"]]
        cursor, more = page["cursor"], page["more"]
    assert sorted(seen) == [f"w{i}" for i in range(5)]
