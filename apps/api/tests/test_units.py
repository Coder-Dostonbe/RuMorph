"""Tests that need no database: tokens, passwords, ids, settings."""

import asyncio
import json
import uuid
from types import SimpleNamespace

import pytest

from tilsim_api import passwords, tokens
from tilsim_api.config import ConfigError, Settings
from tilsim_api.errors import ApiError
from tilsim_api.ids import uuid7

SECRET = b"s" * 40


def issue(**kw):
    values = dict(user_id="u1", role="user", device_id="d1", now=1000, ttl=60)
    values.update(kw)
    return tokens.issue_access_token(SECRET, **values)


def test_access_token_round_trip():
    claims = tokens.verify_access_token(SECRET, issue(), now=1010)
    assert (claims.user_id, claims.role, claims.device_id, claims.expires_at) == ("u1", "user", "d1", 1060)


@pytest.mark.parametrize("now", [1060, 2000])
def test_expired_access_token_is_refused(now):
    with pytest.raises(ApiError) as err:
        tokens.verify_access_token(SECRET, issue(), now=now)
    assert err.value.status == 401


def test_wrong_secret_and_tampering_are_refused():
    token = issue()
    with pytest.raises(ApiError):
        tokens.verify_access_token(b"t" * 40, token, now=1001)
    header, body, sig = token.split(".")
    forged = tokens._b64url(json.dumps({"sub": "u1", "role": "admin", "did": "d1", "iat": 1000, "exp": 9999,
                                        "typ": "access"}).encode())
    with pytest.raises(ApiError):
        tokens.verify_access_token(SECRET, f"{header}.{forged}.{sig}", now=1001)


def test_alg_none_is_refused():
    none_header = tokens._b64url(b'{"alg":"none","typ":"JWT"}')
    _, body, _ = issue().split(".")
    with pytest.raises(ApiError):
        tokens.verify_access_token(SECRET, f"{none_header}.{body}.", now=1001)


@pytest.mark.parametrize("bad", ["", "a.b", "a.b.c.d", "not a token"])
def test_malformed_tokens_are_refused(bad):
    with pytest.raises(ApiError):
        tokens.verify_access_token(SECRET, bad, now=1001)


def test_refresh_tokens_are_random_and_hashed():
    a, b = tokens.new_refresh_token(), tokens.new_refresh_token()
    assert a != b and a.startswith("rt_") and len(a) > 40
    assert tokens.hash_refresh_token(a) == tokens.hash_refresh_token(a)
    assert len(tokens.hash_refresh_token(a)) == 32


def run(coro):
    return asyncio.run(coro)


def test_password_hash_and_verify():
    stored = run(passwords.hash_password("to'g'ri parol 123", 1000))
    assert stored.startswith("pbkdf2_sha256$1000$")
    assert run(passwords.verify_password("to'g'ri parol 123", stored))
    assert not run(passwords.verify_password("noto'g'ri", stored))
    a, b = run(passwords.hash_password("x" * 10, 1000)), run(passwords.hash_password("x" * 10, 1000))
    assert a != b  # salted


def test_known_pbkdf2_vector():
    # RFC 6070-style check of the hashlib path; the Web Crypto path is checked against the
    # same value inside Pyodide (tests/js/webcrypto.test.mjs).
    out = run(passwords.stdlib_derive(b"password", b"salt", 1))
    assert out.hex() == "120fb6cffcf8b32c43e7225256c4f837a86548c92ccc35480805987cb70be17b"


@pytest.mark.parametrize("stored", ["", "plain", "md5$1$a$b", "pbkdf2_sha256$x$a$b", "pbkdf2_sha256$1000$!!$!!"])
def test_malformed_hashes_never_verify(stored):
    assert not run(passwords.verify_password("anything", stored))


def test_needs_rehash_when_iterations_rise():
    stored = run(passwords.hash_password("parol-parol", 1000))
    assert not passwords.needs_rehash(stored, 1000)
    assert passwords.needs_rehash(stored, 2000)
    assert passwords.needs_rehash("pbkdf2_sha256$x$a$b", 1000)


def test_default_iterations_fit_cloudflare_web_crypto():
    assert passwords.DEFAULT_ITERATIONS == Settings(jwt_secret=b"k" * 32).pbkdf2_iterations == 100_000


def test_missing_pbkdf2_is_reported(monkeypatch):
    monkeypatch.delattr(passwords.hashlib, "pbkdf2_hmac")
    with pytest.raises(RuntimeError, match="webcrypto"):
        run(passwords.stdlib_derive(b"p", b"s", 1))


def test_uuid7_is_time_ordered_and_valid():
    a, b = uuid7(1_000), uuid7(2_000)
    assert a.version == 7 and a.variant == uuid.RFC_4122
    assert a < b
    assert len({uuid7() for _ in range(1000)}) == 1000


def env(**kw):
    return SimpleNamespace(**kw)


def test_settings_from_env():
    s = Settings.from_env(env(JWT_SECRET="k" * 32, ALLOW_REGISTRATION="true",
                              CORS_ORIGINS="http://tauri.localhost, http://localhost:1420"))
    assert s.allow_registration and s.pbkdf2_iterations == 100_000
    assert s.cors_origins == {"http://tauri.localhost", "http://localhost:1420"}


def test_registration_is_closed_by_default():
    assert not Settings.from_env(env(JWT_SECRET="k" * 32)).allow_registration


@pytest.mark.parametrize("bad", [env(), env(JWT_SECRET="short")])
def test_settings_refuse_weak_configuration(bad):
    with pytest.raises(ConfigError):
        Settings.from_env(bad)
