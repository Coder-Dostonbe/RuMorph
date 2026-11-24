"""Sync, the account overview and signing out other devices (see tilsim_api/sync.py)."""

import uuid

import pytest
from conftest import device, make_settings

from tilsim_api import sync

PASSWORD = "juda-maxfiy-parol"
T0 = "2026-11-20T09:00:00.000Z"


def register(api, email="doston@example.com", dev=None):
    r = api.call("POST", "/v1/auth/register",
                 {"email": email, "password": PASSWORD, "device": dev or device()})
    assert r.status == 201, r.body
    return r.json()


def login(api, email="doston@example.com", dev=None):
    r = api.call("POST", "/v1/auth/login", {"email": email, "password": PASSWORD, "device": dev or device()})
    assert r.status == 200, r.body
    return r.json()


def word(id_=None, version=1, updated_at=T0, **extra):
    row = {
        "id": id_ or str(uuid.uuid4()), "created_at": T0, "updated_at": updated_at, "deleted_at": None,
        "version": version, "lexeme_id": "книга|NOUN,inan,femn", "lemma": "книга", "pos": "NOUN",
        "translation": "", "note": "", "examples": [{"ru": "Это книга.", "uz": "Bu kitob."}], "status": "learning",
    }
    row.update(extra)
    return row


def review(card_id, id_=None):
    return {"id": id_ or str(uuid.uuid4()), "created_at": T0, "updated_at": T0, "deleted_at": None, "version": 1,
            "card_id": card_id, "reviewed_at": T0, "grade": 2, "interval_after": 1.0, "ease_after": 2.5}


def push(api, token, *changes):
    return api.call("POST", "/v1/sync/push", {"changes": [{"table": t, "row": r} for t, r in changes]}, token=token)


def pull(api, token, since=0):
    r = api.call("GET", f"/v1/sync/pull?since={since}", token=token)
    assert r.status == 200, r.body
    return r.json()


def test_sync_needs_a_token(api):
    assert api.call("POST", "/v1/sync/push", {"changes": []}).status == 401
    assert api.call("GET", "/v1/sync/pull").status == 401
    assert api.call("GET", "/v1/account").status == 401


def test_rows_pushed_on_one_device_arrive_on_the_other(api):
    pc = register(api)
    phone = login(api, dev=device(platform="android"))
    row = word()
    r = push(api, pc["access_token"], ("user_vocabulary", row))
    assert r.status == 200
    assert r.json() == {"accepted": [{"table": "user_vocabulary", "id": row["id"]}], "conflicts": [], "rejected": []}

    got = pull(api, phone["access_token"])
    assert got["changes"] == [{"table": "user_vocabulary", "row": row}]
    assert got["more"] is False and got["cursor"] > 0
    again = pull(api, phone["access_token"], since=got["cursor"])
    assert again["changes"] == [] and again["cursor"] == got["cursor"]


def test_higher_version_wins_and_the_loser_gets_the_stored_row(api):
    pc = register(api)
    row = word(version=3, note="PC")
    push(api, pc["access_token"], ("user_vocabulary", row))

    older = dict(row, version=2, note="old phone edit", updated_at="2026-11-21T09:00:00Z")
    r = push(api, pc["access_token"], ("user_vocabulary", older)).json()
    assert r["accepted"] == [] and r["conflicts"] == [{"table": "user_vocabulary", "row": row}]

    newer = dict(row, version=4, note="new")
    assert push(api, pc["access_token"], ("user_vocabulary", newer)).json()["accepted"]
    assert pull(api, pc["access_token"])["changes"][-1]["row"]["note"] == "new"


def test_equal_versions_are_decided_by_updated_at(api):
    pc = register(api)
    row = word(version=2, note="first")
    push(api, pc["access_token"], ("user_vocabulary", row))
    later = dict(row, note="second", updated_at="2026-11-20T09:00:01Z")
    assert push(api, pc["access_token"], ("user_vocabulary", later)).json()["accepted"]
    same = dict(later, note="replay")
    assert push(api, pc["access_token"], ("user_vocabulary", same)).json()["conflicts"]


def test_deletions_are_synced(api):
    pc = register(api)
    row = word()
    push(api, pc["access_token"], ("user_vocabulary", row))
    gone = dict(row, version=2, deleted_at="2026-11-20T10:00:00Z", updated_at="2026-11-20T10:00:00Z")
    push(api, pc["access_token"], ("user_vocabulary", gone))
    assert pull(api, pc["access_token"])["changes"] == [{"table": "user_vocabulary", "row": gone}]


def test_pull_moves_a_changed_row_to_the_end(api):
    pc = register(api)
    a, b = word(lexeme_id="a"), word(lexeme_id="b")
    push(api, pc["access_token"], ("user_vocabulary", a), ("user_vocabulary", b))
    first = pull(api, pc["access_token"])
    push(api, pc["access_token"], ("user_vocabulary", dict(a, version=2)))
    later = pull(api, pc["access_token"], since=first["cursor"])
    assert [c["row"]["lexeme_id"] for c in later["changes"]] == ["a"]


def test_pull_pages(api, monkeypatch):
    monkeypatch.setattr(sync, "PULL_LIMIT", 2)
    pc = register(api)
    push(api, pc["access_token"], *[("user_vocabulary", word(lexeme_id=str(i))) for i in range(5)])
    seen, cursor, more = [], 0, True
    while more:
        page = pull(api, pc["access_token"], since=cursor)
        seen += [c["row"]["lexeme_id"] for c in page["changes"]]
        cursor, more = page["cursor"], page["more"]
    assert seen == ["0", "1", "2", "3", "4"]


def test_users_never_see_each_others_rows(api):
    a = register(api)
    b = register(api, email="mehmon@example.com")
    row = word()
    push(api, a["access_token"], ("user_vocabulary", row))
    assert pull(api, b["access_token"])["changes"] == []
    # The same id from another user is a separate record, not an overwrite.
    push(api, b["access_token"], ("user_vocabulary", dict(row, version=9, note="b")))
    assert pull(api, a["access_token"])["changes"][0]["row"]["note"] == ""


@pytest.mark.parametrize(
    ("table", "change", "code"),
    [
        ("user_vocabulary", {"status": "forgotten"}, "invalid_status"),
        ("user_vocabulary", {"version": 0}, "invalid_version"),
        ("user_vocabulary", {"id": "not-a-uuid"}, "invalid_id"),
        ("user_vocabulary", {"updated_at": "yesterday"}, "invalid_updated_at"),
        ("user_vocabulary", {"updated_at": "2026-11-20T09:00:00"}, "invalid_updated_at"),
        ("user_vocabulary", {"lemma": ""}, "invalid_lemma"),
        ("user_vocabulary", {"note": "x" * 5001}, "invalid_note"),
        ("user_vocabulary", {"examples": [{"ru": "a"}]}, "invalid_examples"),
        ("user_vocabulary", {"extra": 1}, "invalid_fields"),
        ("user_vocabulary", {"version": True}, "invalid_version"),
        ("nope", {}, "invalid_table"),
    ],
)
def test_bad_rows_are_refused_one_by_one(api, table, change, code):
    pc = register(api)
    good = word(lexeme_id="good")
    r = push(api, pc["access_token"], (table, word(**change)), ("user_vocabulary", good)).json()
    assert [x["code"] for x in r["rejected"]] == [code]
    assert r["accepted"] == [{"table": "user_vocabulary", "id": good["id"]}]


def test_missing_field_is_refused(api):
    pc = register(api)
    row = word()
    del row["note"]
    r = push(api, pc["access_token"], ("user_vocabulary", row)).json()
    assert r["rejected"][0]["code"] == "invalid_fields"


def test_test_result_cannot_have_more_correct_than_total(api):
    pc = register(api)
    row = {"id": str(uuid.uuid4()), "created_at": T0, "updated_at": T0, "deleted_at": None, "version": 1,
           "kind": "ru_uz", "taken_at": T0, "total": 3, "correct": 4, "details": []}
    assert push(api, pc["access_token"], ("test_results", row)).json()["rejected"][0]["code"] == "invalid_correct"


def test_every_table_round_trips(api):
    pc = register(api)
    card = str(uuid.uuid4())
    text = str(uuid.uuid4())
    base = {"created_at": T0, "updated_at": T0, "deleted_at": None, "version": 1}
    rows = [
        ("user_vocabulary", word()),
        ("flashcards", {"id": card, **base, "lexeme_id": "x", "direction": "uz_ru", "due_at": "2026-11-21T09:00:00+00:00",
                        "interval_days": 1, "ease": 2.36, "reps": 1, "lapses": 0, "last_review_at": T0}),
        ("review_history", review(card)),
        ("reading_texts", {"id": text, **base, "title": "Т", "body": "Я читаю.", "source": ""}),
        ("reading_history", {"id": str(uuid.uuid4()), **base, "text_id": text, "read_at": T0, "words": 2,
                             "looked_up": 1, "duration_ms": 5000}),
        ("test_results", {"id": str(uuid.uuid4()), **base, "kind": "ru_uz", "taken_at": T0, "total": 2, "correct": 1,
                          "details": [{"lemma": "книга", "given": "kitob"}]}),
    ]
    r = push(api, pc["access_token"], *rows).json()
    assert len(r["accepted"]) == 6 and not r["rejected"]
    assert sorted((c["table"], c["row"]["id"]) for c in pull(api, pc["access_token"])["changes"]) == \
        sorted((t, row["id"]) for t, row in rows)


def test_duplicates_in_one_push_keep_the_newest(api):
    pc = register(api)
    row = word()
    r = push(api, pc["access_token"], ("user_vocabulary", dict(row, version=2, note="new")),
             ("user_vocabulary", row)).json()
    assert len(r["accepted"]) == 1
    assert pull(api, pc["access_token"])["changes"][0]["row"]["note"] == "new"


def test_push_limits(api):
    pc = register(api)
    many = [("user_vocabulary", word()) for _ in range(sync.MAX_PUSH_ROWS + 1)]
    r = push(api, pc["access_token"], *many)
    assert r.status == 400 and r.json()["error"]["code"] == "too_many_changes"
    r = api.call("POST", "/v1/sync/push", {"changes": "x"}, token=pc["access_token"])
    assert r.json()["error"]["code"] == "invalid_changes"
    r = api.call("GET", "/v1/sync/pull?since=-1", token=pc["access_token"])
    assert r.status == 400 and r.json()["error"]["code"] == "invalid_since"


def test_large_reading_text_fits_in_a_push(api):
    pc = register(api)
    text = {"id": str(uuid.uuid4()), "created_at": T0, "updated_at": T0, "deleted_at": None, "version": 1,
            "title": "Uzun", "body": "Я" * 50_000, "source": ""}
    assert push(api, pc["access_token"], ("reading_texts", text)).json()["accepted"]


def test_account_shows_progress_and_devices(api):
    pc_dev = device()
    pc = register(api, dev=pc_dev)
    phone = login(api, dev={**device(platform="android"), "name": "Telefon"})
    push(api, pc["access_token"], ("user_vocabulary", word(lexeme_id="a", status="known")),
         ("user_vocabulary", word(lexeme_id="b")),
         ("user_vocabulary", word(lexeme_id="c", deleted_at=T0)),
         ("review_history", review(str(uuid.uuid4()))))
    api.clock.advance(minutes=5)
    pull(api, phone["access_token"])

    r = api.call("GET", "/v1/account", token=phone["access_token"])
    assert r.status == 200
    body = r.json()
    assert body["user"]["email"] == "doston@example.com"
    p = body["progress"]
    assert (p["words"], p["known_words"], p["reviews"], p["cards"], p["tests"]) == (2, 1, 1, 0, 0)
    assert p["last_change_at"] is not None
    names = [(d["name"], d["platform"], d["current"], d["signed_in"]) for d in body["devices"]]
    assert names == [("Telefon", "android", True, True), ("Test PC", "windows", False, True)]
    phone_row = body["devices"][0]
    assert phone_row["last_sync_at"] == phone_row["last_seen_at"]
    assert body["devices"][1]["last_sync_at"] is None   # the PC pushed but never pulled


def test_signing_out_another_device(api):
    pc = register(api)
    phone = login(api, dev=device(platform="android"))
    devices = api.call("GET", "/v1/account", token=pc["access_token"]).json()["devices"]
    phone_id = next(d["id"] for d in devices if not d["current"])

    r = api.call("POST", "/v1/devices/revoke", {"device_id": phone_id}, token=pc["access_token"])
    assert r.status == 204
    # The phone's access token is still unexpired, but sync refuses a signed-out device ...
    assert api.call("GET", "/v1/sync/pull", token=phone["access_token"]).status == 401
    # ... and its refresh token no longer works.
    assert api.call("POST", "/v1/auth/refresh", {"refresh_token": phone["refresh_token"]}).status == 401
    after = api.call("GET", "/v1/account", token=pc["access_token"]).json()["devices"]
    assert [d["signed_in"] for d in after if d["id"] == phone_id] == [False]
    (log,) = api.query("SELECT meta FROM audit_log WHERE action = 'device_revoked'")
    assert phone_id in log["meta"]


def test_revoke_rules(api):
    pc = register(api)
    other = register(api, email="mehmon@example.com")
    own = api.call("GET", "/v1/account", token=pc["access_token"]).json()["devices"][0]["id"]
    foreign = api.call("GET", "/v1/account", token=other["access_token"]).json()["devices"][0]["id"]
    assert api.call("POST", "/v1/devices/revoke", {"device_id": own}, token=pc["access_token"]).json()["error"]["code"] \
        == "current_device"
    r = api.call("POST", "/v1/devices/revoke", {"device_id": foreign}, token=pc["access_token"])
    assert r.status == 404
    r = api.call("POST", "/v1/devices/revoke", {"device_id": "x"}, token=pc["access_token"])
    assert r.json()["error"]["code"] == "invalid_device"


def test_signed_out_device_cannot_push(api):
    pc = register(api)
    api.call("POST", "/v1/auth/logout", {"refresh_token": pc["refresh_token"]})
    assert push(api, pc["access_token"], ("user_vocabulary", word())).status == 401


def test_new_accounts_per_network_are_limited(api):
    api.settings = make_settings(max_registrations_per_ip=2)
    register(api, email="a@example.com")
    register(api, email="b@example.com")
    r = api.call("POST", "/v1/auth/register", {"email": "c@example.com", "password": PASSWORD, "device": device()})
    assert r.status == 429 and r.json()["error"]["code"] == "too_many_attempts"
    api.clock.advance(hours=1, seconds=1)
    register(api, email="c@example.com")
