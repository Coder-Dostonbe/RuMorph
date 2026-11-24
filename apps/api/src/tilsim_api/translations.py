"""Word translations shared by every device (db/postgres/migrations/0003_translations.sql).

Reading is public: the translations are the app's content, not anyone's data. Writing needs an
admin account. For each word the change with the later updated_at is kept; an older one is
answered with the stored entry (`conflicts`), so the admin's device takes it.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from typing import Any

from .errors import ApiError, bad_request
from .sync import RowError, _timestamp

MAX_PUSH = 200
PULL_LIMIT = 2000
MAX_TEXT = 200
MAX_EXAMPLES = 3
MAX_EXAMPLE = 300
FIELDS = {"lexeme_id", "lemma", "translation", "updated_at", "deleted_at"}
OPTIONAL = {"examples", "verified"}   # older apps send entries without them
# A change dated further ahead than this comes from a wrong clock; it would win over every later edit.
MAX_CLOCK_AHEAD = timedelta(days=1)
# Writes take this lock, so server_seq values become visible in order and a pull never skips one.
WRITE_LOCK = 7_301_355


def _text(value: Any, low: int) -> bool:
    return isinstance(value, str) and low <= len(value) <= MAX_TEXT and value == value.strip()


def _example(value: Any) -> bool:
    return (isinstance(value, dict) and set(value) == {"ru", "uz"}
            and all(isinstance(value[k], str) and 1 <= len(value[k]) <= MAX_EXAMPLE and value[k] == value[k].strip()
                    for k in ("ru", "uz")))


def check_entry(entry: Any, now: datetime) -> dict[str, Any]:
    if not isinstance(entry, dict) or not FIELDS <= set(entry) <= FIELDS | OPTIONAL:
        raise RowError("invalid_fields")
    entry = {"examples": [], "verified": True, **entry}
    if not isinstance(entry["examples"], list) or len(entry["examples"]) > MAX_EXAMPLES \
            or not all(_example(x) for x in entry["examples"]):
        raise RowError("invalid_examples")
    if not isinstance(entry["verified"], bool):
        raise RowError("invalid_verified")
    if not (isinstance(entry["lexeme_id"], str) and 1 <= len(entry["lexeme_id"]) <= 200):
        raise RowError("invalid_lexeme_id")
    if not _text(entry["lemma"], 1):
        raise RowError("invalid_lemma")
    if not _timestamp(entry["updated_at"]) or datetime.fromisoformat(entry["updated_at"]) > now + MAX_CLOCK_AHEAD:
        raise RowError("invalid_updated_at")
    if entry["deleted_at"] is not None and not _timestamp(entry["deleted_at"]):
        raise RowError("invalid_deleted_at")
    if not _text(entry["translation"], 0 if entry["deleted_at"] else 1):
        raise RowError("invalid_translation")
    return dict(entry)


def _entry(row: Any) -> dict[str, Any]:
    return {
        "lexeme_id": row["lexeme_id"],
        "lemma": row["lemma"],
        "translation": row["translation"],
        "updated_at": row["updated_at"].isoformat(),
        "deleted_at": row["deleted_at"].isoformat() if row["deleted_at"] else None,
        "examples": json.loads(row["examples"]) if isinstance(row["examples"], str) else row["examples"],
        "verified": row["verified"],
    }


async def require_admin(conn, user_id: str) -> None:
    role = await conn.fetchval(
        "SELECT role FROM users WHERE id = $1 AND disabled_at IS NULL", uuid.UUID(user_id),
    )
    if role != "admin":
        raise ApiError(403, "not_admin", "only an admin account can change translations")


async def push(conn, *, user_id: str, body: dict[str, Any], now: datetime) -> dict[str, Any]:
    changes = body.get("changes")
    if not isinstance(changes, list):
        raise bad_request("invalid_changes", "changes must be a list")
    if len(changes) > MAX_PUSH:
        raise bad_request("too_many_changes", f"send at most {MAX_PUSH} changes at a time")
    entries: dict[str, dict[str, Any]] = {}
    rejected: list[dict[str, str]] = []
    for raw in changes:
        try:
            entry = check_entry(raw, now)
        except RowError as exc:
            lexeme = raw.get("lexeme_id") if isinstance(raw, dict) and isinstance(raw.get("lexeme_id"), str) else ""
            rejected.append({"lexeme_id": lexeme[:200], "code": exc.code})
            continue
        known = entries.get(entry["lexeme_id"])
        if known is None or datetime.fromisoformat(entry["updated_at"]) > datetime.fromisoformat(known["updated_at"]):
            entries[entry["lexeme_id"]] = entry
    rows = list(entries.values())

    accepted: list[str] = []
    conflicts: list[dict[str, Any]] = []
    async with conn.transaction():
        await require_admin(conn, user_id)
        await conn.execute("SELECT pg_advisory_xact_lock($1)", WRITE_LOCK)
        if rows:
            written = await conn.fetch(
                """
                INSERT INTO translations AS t
                    (lexeme_id, lemma, translation, updated_at, deleted_at, examples, verified, updated_by)
                SELECT e.lexeme_id, e.lemma, e.translation, e.updated_at::timestamptz, e.deleted_at::timestamptz,
                       e.examples::jsonb, e.verified, $1
                FROM unnest($2::text[], $3::text[], $4::text[], $5::text[], $6::text[], $7::text[], $8::bool[])
                     AS e(lexeme_id, lemma, translation, updated_at, deleted_at, examples, verified)
                ON CONFLICT (lexeme_id) DO UPDATE
                SET lemma = EXCLUDED.lemma, translation = EXCLUDED.translation, updated_at = EXCLUDED.updated_at,
                    deleted_at = EXCLUDED.deleted_at, examples = EXCLUDED.examples, verified = EXCLUDED.verified,
                    updated_by = EXCLUDED.updated_by,
                    server_seq = nextval('translation_seq'), received_at = now()
                WHERE EXCLUDED.updated_at > t.updated_at
                RETURNING lexeme_id
                """,
                uuid.UUID(user_id),
                [e["lexeme_id"] for e in rows], [e["lemma"] for e in rows], [e["translation"] for e in rows],
                [e["updated_at"] for e in rows], [e["deleted_at"] for e in rows],
                [json.dumps(e["examples"], ensure_ascii=False) for e in rows], [e["verified"] for e in rows],
            )
            accepted = sorted(w["lexeme_id"] for w in written)
            stale = [e["lexeme_id"] for e in rows if e["lexeme_id"] not in set(accepted)]
            if stale:
                current = await conn.fetch(
                    "SELECT * FROM translations WHERE lexeme_id = ANY($1::text[]) ORDER BY lexeme_id", stale,
                )
                conflicts = [_entry(r) for r in current]
    return {"accepted": accepted, "conflicts": conflicts, "rejected": rejected}


async def pull(conn, *, since: int) -> dict[str, Any]:
    rows = await conn.fetch(
        "SELECT * FROM translations WHERE server_seq > $1 ORDER BY server_seq LIMIT $2", since, PULL_LIMIT + 1,
    )
    more = len(rows) > PULL_LIMIT
    rows = rows[:PULL_LIMIT]
    return {
        "changes": [_entry(r) for r in rows],
        "cursor": rows[-1]["server_seq"] if rows else since,
        "more": more,
    }
