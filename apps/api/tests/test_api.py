"""End-to-end tests of the API against a real PostgreSQL (see conftest.py)."""

import asyncio

import pytest
from conftest import ORIGIN, device, make_settings

from tilsim_api.app import handle
from tilsim_api.http import Request

PASSWORD = "juda-maxfiy-parol"


def register(api, email="doston@example.com", password=PASSWORD, **extra):
    body = {"email": email, "password": password, "display_name": "Doston", "device": device()}
    body.update(extra)
    return api.call("POST", "/v1/auth/register", body)


def login(api, email="doston@example.com", password=PASSWORD, dev=None):
    return api.call("POST", "/v1/auth/login", {"email": email, "password": password, "device": dev or device()})


# --- health, routing, CORS ------------------------------------------------------------------------

def test_health_reports_database(api):
    r = api.call("GET", "/health")
    assert r.status == 200
    assert r.json() == {"status": "ok", "service": "tilsim-api", "version": "0.1.0", "database": "ok"}


def test_health_says_when_database_is_down(api):
    async def broken():
        raise OSError("connection refused")

    r = api.call("GET", "/health", ctx=api.context(connect=broken))
    assert r.status == 200 and r.json()["database"] == "unavailable"


def test_unknown_path_and_method(api):
    assert api.call("GET", "/nope").json()["error"]["code"] == "not_found"
    r = api.call("GET", "/v1/auth/login")
    assert r.status == 405 and r.json()["error"]["code"] == "method_not_allowed"


def test_cors_only_for_listed_origins(api):
    ok = api.call("OPTIONS", "/v1/auth/login", headers={"origin": ORIGIN})
    assert ok.status == 204 and ok.headers["access-control-allow-origin"] == ORIGIN
    bad = api.call("OPTIONS", "/v1/auth/login", headers={"origin": "https://evil.example"})
    assert "access-control-allow-origin" not in bad.headers
    assert api.call("GET", "/health").headers["access-control-allow-origin"] == ORIGIN


def test_body_must_be_json_object(api):
    assert api.call("POST", "/v1/auth/login", raw=b"{oops").json()["error"]["code"] == "invalid_json"
    assert api.call("POST", "/v1/auth/login", raw=b"[1]").json()["error"]["code"] == "invalid_json"
    r = api.call("POST", "/v1/auth/login", raw=b"{}", headers={"content-type": "text/plain"})
    assert r.status == 415
    assert api.call("POST", "/v1/auth/login", raw=b"{" + b" " * 70_000 + b"}").status == 413


def test_missing_configuration_is_a_generic_500(api):
    r = api.call("POST", "/v1/auth/login", {}, ctx=api.context(settings=None, config_error="JWT_SECRET missing"))
    assert r.status == 500 and r.json()["error"] == {"code": "internal", "message": "the server is not configured"}


def test_unexpected_errors_do_not_leak(api, capsys):
    async def boom():
        raise RuntimeError("secret detail")

    class Exploding:
        async def fetchval(self, *a):
            raise RuntimeError("secret detail")

        async def close(self):
            pass

    async def connect():
        return Exploding()

    r = api.call("GET", "/v1/me", ctx=api.context(connect=connect), token="x.y.z")
    assert r.status == 401  # token checked before the database
    r = api.call("POST", "/v1/auth/login", {"email": "a@b.co", "password": "x" * 12, "device": device()},
                 ctx=api.context(connect=connect))
    assert r.status == 500 and "secret detail" not in r.body
    assert "secret detail" in capsys.readouterr().err


# --- registration ---------------------------------------------------------------------------------

def test_first_account_is_admin_then_users(api):
    first = register(api)
    assert first.status == 201
    body = first.json()
    assert body["user"]["role"] == "admin" and body["user"]["email"] == "doston@example.com"
    assert body["token_type"] == "Bearer" and body["refresh_token"].startswith("rt_")
    assert "_token_id" not in body
    second = register(api, email="Mehmon@Example.com ")
    assert second.json()["user"]["role"] == "user"
    assert second.json()["user"]["email"] == "mehmon@example.com"


def test_email_is_unique_case_insensitively(api):
    register(api)
    r = register(api, email="DOSTON@example.com")
    assert r.status == 409 and r.json()["error"]["code"] == "email_taken"


def test_registration_can_be_closed(api):
    api.settings = make_settings(allow_registration=False)
    r = register(api)
    assert r.status == 403 and r.json()["error"]["code"] == "registration_closed"


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ({"password": "short"}, "weak_password"),
        ({"password": "x" * 201}, "invalid_password"),
        ({"email": "not-an-email"}, "invalid_email"),
        ({"email": 42}, "invalid_email"),
        ({"device": {"id": "nope", "platform": "windows"}}, "invalid_device"),
        ({"device": {"id": "8f1e0c1e-3b1a-4c55-9a0e-1f2d3c4b5a69", "platform": "ios"}}, "invalid_device"),
        ({"display_name": "x" * 81}, "invalid_field"),
    ],
)
def test_registration_validates_input(api, change, code):
    r = register(api, **change)
    assert r.status == 400 and r.json()["error"]["code"] == code


def test_password_is_stored_hashed(api):
    register(api)
    (row,) = api.query("SELECT password_hash FROM users")
    assert PASSWORD not in row["password_hash"] and row["password_hash"].startswith("pbkdf2_sha256$")


# --- login and rate limiting ----------------------------------------------------------------------

def test_login_and_me(api):
    register(api)
    r = login(api)
    assert r.status == 200
    me = api.call("GET", "/v1/me", token=r.json()["access_token"])
    assert me.status == 200 and me.json()["user"]["email"] == "doston@example.com"


def test_wrong_password_and_unknown_email_look_the_same(api):
    register(api)
    a, b = login(api, password="wrong-password"), login(api, email="nobody@example.com")
    assert a.status == b.status == 401
    assert a.json() == b.json() == {"error": {"code": "invalid_credentials", "message": "wrong email or password"}}


def test_too_many_failures_block_then_expire(api):
    register(api)
    for _ in range(5):
        assert login(api, password="wrong-password").status == 401
    blocked = login(api)  # even the right password is refused while blocked
    assert blocked.status == 429 and blocked.json()["error"]["code"] == "too_many_attempts"
    assert blocked.headers["retry-after"] == "900"
    api.clock.advance(minutes=16)
    assert login(api).status == 200


def test_success_resets_the_failure_count(api):
    register(api)
    for _ in range(4):
        login(api, password="wrong-password")
    assert login(api).status == 200
    for _ in range(4):
        login(api, password="wrong-password")
    assert login(api).status == 200


def test_login_upgrades_old_password_hashes(api):
    register(api)
    api.settings = make_settings(pbkdf2_iterations=2_000)
    assert login(api).status == 200
    (row,) = api.query("SELECT password_hash FROM users")
    assert row["password_hash"].startswith("pbkdf2_sha256$2000$")


def test_same_device_is_reused(api):
    dev = device()
    register(api, device=dev)
    login(api, dev=dev)
    login(api, dev={**dev, "name": "Yangi nom"})
    rows = api.query("SELECT name FROM devices")
    assert len(rows) == 1 and rows[0]["name"] == "Yangi nom"


# --- access tokens --------------------------------------------------------------------------------

def test_me_needs_a_valid_token(api):
    assert api.call("GET", "/v1/me").status == 401
    assert api.call("GET", "/v1/me", token="garbage").status == 401
    token = register(api).json()["access_token"]
    api.clock.advance(minutes=16)
    r = api.call("GET", "/v1/me", token=token)
    assert r.status == 401 and r.headers["www-authenticate"] == "Bearer"


def test_token_signed_with_another_secret_is_refused(api):
    token = register(api).json()["access_token"]
    api.settings = make_settings(jwt_secret=b"y" * 40)
    assert api.call("GET", "/v1/me", token=token).status == 401


# --- refresh rotation and logout ------------------------------------------------------------------

def refresh(api, token):
    return api.call("POST", "/v1/auth/refresh", {"refresh_token": token})


def test_refresh_rotates_tokens(api):
    first = register(api).json()
    api.clock.advance(minutes=20)
    second = refresh(api, first["refresh_token"])
    assert second.status == 200
    new = second.json()
    assert new["refresh_token"] != first["refresh_token"]
    assert api.call("GET", "/v1/me", token=new["access_token"]).status == 200


def test_reusing_a_refresh_token_ends_the_whole_session(api):
    first = register(api).json()
    second = refresh(api, first["refresh_token"]).json()
    stolen = refresh(api, first["refresh_token"])
    assert stolen.status == 401
    # The legitimate newer token is revoked too, so the thief's copy is worthless.
    assert refresh(api, second["refresh_token"]).status == 401
    actions = [r["action"] for r in api.query("SELECT action FROM audit_log ORDER BY id")]
    assert "refresh_reuse" in actions


def test_expired_refresh_token(api):
    first = register(api).json()
    api.clock.advance(days=31)
    assert refresh(api, first["refresh_token"]).status == 401


@pytest.mark.parametrize("bad", ["", "rt_nope", "no-prefix", None, 5])
def test_invalid_refresh_tokens(api, bad):
    assert refresh(api, bad).status == 401


def test_logout_revokes_the_session(api):
    tokens = register(api).json()
    r = api.call("POST", "/v1/auth/logout", {"refresh_token": tokens["refresh_token"]})
    assert r.status == 204
    assert refresh(api, tokens["refresh_token"]).status == 401
    # Logging out twice is harmless.
    assert api.call("POST", "/v1/auth/logout", {"refresh_token": tokens["refresh_token"]}).status == 204


def test_sessions_on_two_devices_are_independent(api):
    a = register(api).json()
    b = login(api, dev=device(platform="android")).json()
    api.call("POST", "/v1/auth/logout", {"refresh_token": a["refresh_token"]})
    assert refresh(api, b["refresh_token"]).status == 200


# --- audit log ------------------------------------------------------------------------------------

def test_audit_log_never_contains_secrets(api):
    tokens = register(api).json()
    login(api, password="wrong-password")
    refresh(api, tokens["refresh_token"])
    dump = str(api.query("SELECT * FROM audit_log")) + str(api.query("SELECT * FROM auth_attempts"))
    for secret in (PASSWORD, "wrong-password", tokens["refresh_token"], tokens["access_token"]):
        assert secret not in dump
    actions = [r["action"] for r in api.query("SELECT action FROM audit_log ORDER BY id")]
    assert actions == ["register", "login_failed"]  # refresh is not audited, only reuse is


def test_handle_works_with_trailing_slash(api):
    request = Request("GET", "https://api.test/health/", {}, b"")
    response = asyncio.run(handle(request, api.context()))
    assert response.status == 200
