"""Routing, CORS and request handling. `handle` never raises: every failure
becomes a JSON error response, and unexpected errors are logged with a
traceback but answered with a generic "internal" code."""

from __future__ import annotations

import sys
import traceback
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from . import SERVICE, __version__, auth, sync, tokens, validation
from .config import ConfigError, Settings
from .errors import ApiError, unauthorized
from .http import Request, Response, error_response, json_response
from .passwords import Derive, stdlib_derive

Connect = Callable[[], Awaitable[Any]]


@dataclass
class Context:
    """Everything a handler needs from the outside world; tests pass their own."""
    settings: Settings | None
    connect: Connect
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)
    config_error: str | None = None
    # PBKDF2 implementation: hashlib on CPython, Web Crypto in the Worker (Pyodide).
    derive: Derive = stdlib_derive


Handler = Callable[[Request, Context], Awaitable[Response]]


@asynccontextmanager
async def _db(ctx: Context):
    try:
        conn = await ctx.connect()
    except Exception as exc:  # noqa: BLE001
        print(f"database connection failed: {exc!r}", file=sys.stderr)
        raise ApiError(503, "database_unavailable", "the database is not reachable") from None
    try:
        yield conn
    finally:
        await conn.close()


def _settings(ctx: Context) -> Settings:
    if ctx.settings is None:
        print(f"configuration error: {ctx.config_error}", file=sys.stderr)
        raise ApiError(500, "internal", "the server is not configured")
    return ctx.settings


def _bearer(request: Request, settings: Settings, now: datetime) -> tokens.AccessClaims:
    header = request.header("authorization") or ""
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise unauthorized()
    return tokens.verify_access_token(settings.jwt_secret, token.strip(), now=int(now.timestamp()))


# --- handlers -----------------------------------------------------------------------------------

async def health(request: Request, ctx: Context) -> Response:
    database = "ok"
    try:
        async with _db(ctx) as conn:
            await conn.fetchval("SELECT 1")
    except ApiError:
        database = "unavailable"
    return json_response(200, {"status": "ok", "service": SERVICE, "version": __version__, "database": database})


async def register(request: Request, ctx: Context) -> Response:
    settings = _settings(ctx)
    body = request.json()
    email = validation.email(body.get("email"))
    password = validation.new_password(body.get("password"))
    display_name = validation.optional_text(body.get("display_name"), "display_name", 80)
    device = validation.device(body.get("device"))
    async with _db(ctx) as conn:
        result = await auth.register(conn, settings, email=email, password=password, display_name=display_name,
                                     device=device, now=ctx.now(), ip=request.ip, derive=ctx.derive)
    return json_response(201, result)


async def login(request: Request, ctx: Context) -> Response:
    settings = _settings(ctx)
    body = request.json()
    try:
        email = validation.email(body.get("email"))
    except ApiError:
        raise auth.INVALID_CREDENTIALS from None
    password = validation.given_password(body.get("password"))
    device = validation.device(body.get("device"))
    async with _db(ctx) as conn:
        result = await auth.login(conn, settings, email=email, password=password, device=device,
                                  now=ctx.now(), ip=request.ip, derive=ctx.derive)
    return json_response(200, result)


async def refresh(request: Request, ctx: Context) -> Response:
    settings = _settings(ctx)
    token = validation.refresh_token(request.json().get("refresh_token"))
    async with _db(ctx) as conn:
        result = await auth.refresh(conn, settings, refresh_token=token, now=ctx.now(), ip=request.ip)
    return json_response(200, result)


async def logout(request: Request, ctx: Context) -> Response:
    _settings(ctx)
    token = validation.refresh_token(request.json().get("refresh_token"))
    async with _db(ctx) as conn:
        await auth.logout(conn, refresh_token=token, now=ctx.now(), ip=request.ip)
    return Response(204)


async def me(request: Request, ctx: Context) -> Response:
    settings = _settings(ctx)
    claims = _bearer(request, settings, ctx.now())
    async with _db(ctx) as conn:
        user = await auth.current_user(conn, claims.user_id)
    return json_response(200, {"user": user})


# Rows of up to 100 records (a reading text alone may be 50 000 characters).
SYNC_BODY_BYTES = 1024 * 1024


async def sync_push(request: Request, ctx: Context) -> Response:
    settings = _settings(ctx)
    claims = _bearer(request, settings, ctx.now())
    body = request.json(max_bytes=SYNC_BODY_BYTES)
    async with _db(ctx) as conn:
        result = await sync.push(conn, user_id=claims.user_id, device_id=claims.device_id, body=body, now=ctx.now())
    return json_response(200, result)


async def sync_pull(request: Request, ctx: Context) -> Response:
    settings = _settings(ctx)
    claims = _bearer(request, settings, ctx.now())
    since = sync.parse_since(request.query("since"))
    async with _db(ctx) as conn:
        result = await sync.pull(conn, user_id=claims.user_id, device_id=claims.device_id, since=since, now=ctx.now())
    return json_response(200, result)


async def account(request: Request, ctx: Context) -> Response:
    settings = _settings(ctx)
    claims = _bearer(request, settings, ctx.now())
    async with _db(ctx) as conn:
        user = await auth.current_user(conn, claims.user_id)
        overview = await sync.account(conn, user_id=claims.user_id, device_id=claims.device_id, now=ctx.now())
    return json_response(200, {"user": user, **overview})


async def revoke_device(request: Request, ctx: Context) -> Response:
    settings = _settings(ctx)
    claims = _bearer(request, settings, ctx.now())
    target = request.json().get("device_id")
    async with _db(ctx) as conn:
        await sync.revoke_device(conn, user_id=claims.user_id, current_device_id=claims.device_id, target=target,
                                 now=ctx.now(), ip=request.ip, audit=auth.audit)
    return Response(204)


ROUTES: dict[tuple[str, str], Handler] = {
    ("GET", "/health"): health,
    ("POST", "/v1/auth/register"): register,
    ("POST", "/v1/auth/login"): login,
    ("POST", "/v1/auth/refresh"): refresh,
    ("POST", "/v1/auth/logout"): logout,
    ("GET", "/v1/me"): me,
    ("GET", "/v1/account"): account,
    ("POST", "/v1/devices/revoke"): revoke_device,
    ("POST", "/v1/sync/push"): sync_push,
    ("GET", "/v1/sync/pull"): sync_pull,
}


# --- dispatch -----------------------------------------------------------------------------------

def _cors_headers(request: Request, ctx: Context) -> dict[str, str]:
    origin = request.header("origin")
    allowed = ctx.settings.cors_origins if ctx.settings else frozenset()
    if not origin or origin not in allowed:
        return {}
    return {
        "access-control-allow-origin": origin,
        "access-control-allow-methods": "GET, POST, PUT, DELETE, OPTIONS",
        "access-control-allow-headers": "authorization, content-type",
        "access-control-max-age": "600",
        "vary": "Origin",
    }


async def handle(request: Request, ctx: Context) -> Response:
    cors = _cors_headers(request, ctx)
    if request.method == "OPTIONS":
        return Response(204, headers=cors)
    path = request.path.rstrip("/") or "/"
    handler = ROUTES.get((request.method, path))
    try:
        if handler is None:
            if any(p == path for (_, p) in ROUTES):
                raise ApiError(405, "method_not_allowed", f"{request.method} is not allowed here")
            raise ApiError(404, "not_found", "no such endpoint")
        response = await handler(request, ctx)
    except ApiError as exc:
        response = error_response(exc)
    except ConfigError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        response = error_response(ApiError(500, "internal", "the server is not configured"))
    except Exception:  # noqa: BLE001 — the boundary must never raise
        traceback.print_exc(file=sys.stderr)
        response = error_response(ApiError(500, "internal", "internal server error"))
    response.headers.update(cors)
    return response
