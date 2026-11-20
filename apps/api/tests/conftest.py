"""Test helpers. API tests run against a real PostgreSQL: set TEST_DATABASE_URL to
an admin connection string (CI uses a postgres service container). A fresh
database is created for the session and dropped afterwards."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import asyncpg
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from tilsim_api.app import Context, handle  # noqa: E402
from tilsim_api.config import Settings  # noqa: E402
from tilsim_api.http import Request, Response  # noqa: E402

TABLES = ["audit_log", "auth_attempts", "refresh_tokens", "user_settings", "devices", "users"]
ORIGIN = "http://tauri.localhost"


def _with_db(url: str, name: str) -> str:
    parts = urlsplit(url)
    return urlunsplit(parts._replace(path=f"/{name}"))


@pytest.fixture(scope="session")
def database_url():
    admin = os.environ.get("TEST_DATABASE_URL")
    if not admin:
        pytest.skip("TEST_DATABASE_URL is not set; API database tests need PostgreSQL")
    name = f"tilsim_test_{uuid.uuid4().hex[:8]}"

    async def create():
        conn = await asyncpg.connect(admin)
        await conn.execute(f'CREATE DATABASE "{name}"')
        await conn.close()

    async def drop():
        conn = await asyncpg.connect(admin)
        await conn.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        await conn.close()

    asyncio.run(create())
    url = _with_db(admin, name)
    import migrate

    asyncio.run(migrate.migrate(url))
    yield url
    asyncio.run(drop())


class Clock:
    def __init__(self) -> None:
        self.value = datetime(2026, 11, 20, 9, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.value

    def advance(self, **kwargs) -> None:
        self.value += timedelta(**kwargs)


class Api:
    """Calls app.handle like the Worker does, with a real database and a controllable clock."""

    def __init__(self, url: str, settings: Settings | None) -> None:
        self.url = url
        self.clock = Clock()
        self.settings = settings

    def context(self, **overrides) -> Context:
        async def connect():
            return await asyncpg.connect(self.url)

        values = {"settings": self.settings, "connect": connect, "now": self.clock}
        values.update(overrides)
        return Context(**values)

    def call(self, method: str, path: str, body=None, *, token: str | None = None, headers=None,
             raw: bytes | None = None, ctx: Context | None = None) -> Response:
        h = {"origin": ORIGIN}
        if body is not None or raw is not None:
            h["content-type"] = "application/json"
        if token:
            h["authorization"] = f"Bearer {token}"
        h.update(headers or {})
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else b"")
        request = Request(method=method, url=f"https://api.test{path}", headers=h, body=data, ip="203.0.113.7")
        return asyncio.run(handle(request, ctx or self.context()))

    def query(self, sql: str, *args):
        async def run():
            conn = await asyncpg.connect(self.url)
            try:
                return await conn.fetch(sql, *args)
            finally:
                await conn.close()

        return asyncio.run(run())


def make_settings(**overrides) -> Settings:
    values = dict(jwt_secret=b"x" * 40, allow_registration=True, cors_origins=frozenset({ORIGIN}),
                  pbkdf2_iterations=1_000)  # fast for tests; production default is 600 000
    values.update(overrides)
    return Settings(**values)


@pytest.fixture
def api(database_url):
    async def clean():
        conn = await asyncpg.connect(database_url)
        await conn.execute(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE")
        await conn.close()

    asyncio.run(clean())
    return Api(database_url, make_settings())


def device(client_id: str | None = None, platform: str = "windows") -> dict:
    return {"id": client_id or str(uuid.uuid4()), "name": "Test PC", "platform": platform}
