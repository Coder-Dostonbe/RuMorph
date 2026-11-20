"""Accounts and sessions: register, sign in, refresh (with rotation), sign out.

Every function takes an open asyncpg connection. Multi-statement changes run
in one transaction.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from . import passwords, tokens
from .config import Settings
from .errors import ApiError
from .ids import uuid7

INVALID_CREDENTIALS = ApiError(401, "invalid_credentials", "wrong email or password")


def user_json(row: Any) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "email": row["email"],
        "display_name": row["display_name"],
        "role": row["role"],
        "created_at": row["created_at"].astimezone(timezone.utc).isoformat(),
    }


async def audit(conn, action: str, *, user_id=None, device_id=None, ip: str | None = None, **meta) -> None:
    await conn.execute(
        "INSERT INTO audit_log (user_id, device_id, action, ip, meta) VALUES ($1, $2, $3, $4, $5::jsonb)",
        user_id, device_id, action, ip, json.dumps(meta),
    )


async def _upsert_device(conn, user_id, device: dict[str, str], now: datetime):
    return await conn.fetchval(
        """
        INSERT INTO devices (id, user_id, client_id, name, platform, created_at, last_seen_at)
        VALUES ($1, $2, $3, $4, $5, $6, $6)
        ON CONFLICT (user_id, client_id)
        DO UPDATE SET name = EXCLUDED.name, platform = EXCLUDED.platform, last_seen_at = EXCLUDED.last_seen_at
        RETURNING id
        """,
        uuid7(), user_id, device["client_id"], device["name"], device["platform"], now,
    )


async def _issue(conn, settings: Settings, user: Any, device_id, now: datetime, family_id=None) -> dict[str, Any]:
    """Creates a refresh token row and returns the full token response for `user`."""
    refresh = tokens.new_refresh_token()
    token_id = uuid7()
    await conn.execute(
        """
        INSERT INTO refresh_tokens (id, user_id, device_id, family_id, token_hash, created_at, expires_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
        token_id, user["id"], device_id, family_id or token_id, tokens.hash_refresh_token(refresh),
        now, now + timedelta(seconds=settings.refresh_ttl),
    )
    access = tokens.issue_access_token(
        settings.jwt_secret, user_id=str(user["id"]), role=user["role"], device_id=str(device_id),
        now=int(now.timestamp()), ttl=settings.access_ttl,
    )
    return {
        "user": user_json(user),
        "access_token": access,
        "access_expires_in": settings.access_ttl,
        "refresh_token": refresh,
        "refresh_expires_in": settings.refresh_ttl,
        "token_type": "Bearer",
        "_token_id": token_id,
    }


def _public(result: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in result.items() if not k.startswith("_")}


async def register(conn, settings: Settings, *, email: str, password: str, display_name: str | None,
                   device: dict[str, str], now: datetime, ip: str | None) -> dict[str, Any]:
    if not settings.allow_registration:
        raise ApiError(403, "registration_closed", "registration is closed")
    password_hash = passwords.hash_password(password, settings.pbkdf2_iterations)
    async with conn.transaction():
        # Serialises concurrent registrations so exactly one first account becomes admin.
        await conn.execute("LOCK TABLE users IN SHARE ROW EXCLUSIVE MODE")
        if await conn.fetchval("SELECT 1 FROM users WHERE email = $1", email):
            raise ApiError(409, "email_taken", "an account with this email already exists")
        role = "user" if await conn.fetchval("SELECT EXISTS (SELECT 1 FROM users)") else "admin"
        user = await conn.fetchrow(
            """
            INSERT INTO users (id, email, password_hash, display_name, role, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $6)
            RETURNING id, email, display_name, role, created_at
            """,
            uuid7(), email, password_hash, display_name, role, now,
        )
        device_id = await _upsert_device(conn, user["id"], device, now)
        result = await _issue(conn, settings, user, device_id, now)
        await audit(conn, "register", user_id=user["id"], device_id=device_id, ip=ip, role=role)
    return _public(result)


async def _too_many_failures(conn, settings: Settings, email: str, now: datetime) -> bool:
    since = now - timedelta(seconds=settings.failed_login_window)
    failures = await conn.fetchval(
        """
        SELECT count(*) FROM auth_attempts
        WHERE email = $1 AND success = false AND created_at > $2
          AND created_at > coalesce(
                (SELECT max(created_at) FROM auth_attempts WHERE email = $1 AND success = true), '-infinity')
        """,
        email, since,
    )
    return failures >= settings.max_failed_logins


async def login(conn, settings: Settings, *, email: str, password: str, device: dict[str, str],
                now: datetime, ip: str | None) -> dict[str, Any]:
    if await _too_many_failures(conn, settings, email, now):
        await audit(conn, "login_blocked", ip=ip, email=email)
        raise ApiError(429, "too_many_attempts", "too many failed attempts, try again later",
                       {"retry-after": str(settings.failed_login_window)})
    user = await conn.fetchrow(
        "SELECT id, email, password_hash, display_name, role, created_at, disabled_at FROM users WHERE email = $1",
        email,
    )
    if user is None:
        passwords.dummy_verify(password, settings.pbkdf2_iterations)
        ok = False
    else:
        ok = passwords.verify_password(password, user["password_hash"]) and user["disabled_at"] is None
    await conn.execute(
        "INSERT INTO auth_attempts (email, ip, success, created_at) VALUES ($1, $2, $3, $4)", email, ip, ok, now,
    )
    if not ok:
        await audit(conn, "login_failed", user_id=user["id"] if user else None, ip=ip)
        raise INVALID_CREDENTIALS

    async with conn.transaction():
        if passwords.needs_rehash(user["password_hash"], settings.pbkdf2_iterations):
            await conn.execute(
                "UPDATE users SET password_hash = $2, updated_at = $3 WHERE id = $1",
                user["id"], passwords.hash_password(password, settings.pbkdf2_iterations), now,
            )
        device_id = await _upsert_device(conn, user["id"], device, now)
        result = await _issue(conn, settings, user, device_id, now)
        await audit(conn, "login", user_id=user["id"], device_id=device_id, ip=ip)
    return _public(result)


async def refresh(conn, settings: Settings, *, refresh_token: str, now: datetime, ip: str | None) -> dict[str, Any]:
    reused = False
    async with conn.transaction():
        row = await conn.fetchrow(
            """
            SELECT t.id, t.user_id, t.device_id, t.family_id, t.expires_at, t.revoked_at,
                   u.email, u.display_name, u.role, u.created_at, u.disabled_at
            FROM refresh_tokens t JOIN users u ON u.id = t.user_id
            WHERE t.token_hash = $1
            FOR UPDATE OF t
            """,
            tokens.hash_refresh_token(refresh_token),
        )
        if row is None:
            raise ApiError(401, "unauthorized", "invalid refresh token")
        if row["revoked_at"] is not None:
            # A used token came back: someone has a copy. End every session in this family.
            # The error is raised after the transaction, so this revocation is committed.
            await conn.execute(
                "UPDATE refresh_tokens SET revoked_at = $2 WHERE family_id = $1 AND revoked_at IS NULL",
                row["family_id"], now,
            )
            await audit(conn, "refresh_reuse", user_id=row["user_id"], device_id=row["device_id"], ip=ip)
            reused = True
        elif row["expires_at"] <= now or row["disabled_at"] is not None:
            raise ApiError(401, "unauthorized", "refresh token expired")
        else:
            user = {"id": row["user_id"], "email": row["email"], "display_name": row["display_name"],
                    "role": row["role"], "created_at": row["created_at"]}
            result = await _issue(conn, settings, user, row["device_id"], now, family_id=row["family_id"])
            await conn.execute(
                "UPDATE refresh_tokens SET revoked_at = $2, replaced_by = $3 WHERE id = $1",
                row["id"], now, result["_token_id"],
            )
            await conn.execute("UPDATE devices SET last_seen_at = $2 WHERE id = $1", row["device_id"], now)
    if reused:
        raise ApiError(401, "unauthorized", "refresh token was already used")
    return _public(result)


async def logout(conn, *, refresh_token: str, now: datetime, ip: str | None) -> None:
    async with conn.transaction():
        row = await conn.fetchrow(
            "UPDATE refresh_tokens SET revoked_at = coalesce(revoked_at, $2) WHERE token_hash = $1 "
            "RETURNING user_id, device_id, family_id",
            tokens.hash_refresh_token(refresh_token), now,
        )
        if row is not None:
            await conn.execute(
                "UPDATE refresh_tokens SET revoked_at = $2 WHERE family_id = $1 AND revoked_at IS NULL",
                row["family_id"], now,
            )
            await audit(conn, "logout", user_id=row["user_id"], device_id=row["device_id"], ip=ip)


async def current_user(conn, user_id: str) -> dict[str, Any]:
    row = await conn.fetchrow(
        "SELECT id, email, display_name, role, created_at FROM users WHERE id = $1 AND disabled_at IS NULL",
        user_id,
    )
    if row is None:
        raise ApiError(401, "unauthorized", "user no longer exists")
    return user_json(row)
