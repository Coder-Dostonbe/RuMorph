"""Sync of the learner's data between devices, and the account overview.

Push: the device sends rows it changed. A row is written when its (version, updated_at) is
higher than the stored one; otherwise the stored row is sent back as a conflict and the
device takes it. Rows that break the field rules are refused one by one (`rejected`).

Pull: rows of the user with server_seq greater than the device's cursor, in server_seq order.

Every field of a row is checked against SPECS before it reaches the database; unknown
fields are refused. The device schema is db/sqlite/migrations/0002_learning.sql.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Any

from .errors import ApiError, bad_request, unauthorized

MAX_PUSH_ROWS = 100
PULL_LIMIT = 500
MAX_JSON_FIELD = 100_000          # characters of a JSON field (examples, details) once encoded
MAX_INT = 2**31 - 1

Check = Callable[[Any], bool]


class RowError(Exception):
    """One row breaks a rule; the rest of the push goes on."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not 10 <= len(value) <= 40:
        return False
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _uuid(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True


def text(min_len: int, max_len: int) -> Check:
    return lambda v: isinstance(v, str) and min_len <= len(v) <= max_len


def number(low: float, high: float) -> Check:
    return lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and low <= v <= high


def integer(low: int, high: int = MAX_INT) -> Check:
    return lambda v: isinstance(v, int) and not isinstance(v, bool) and low <= v <= high


def one_of(*values: str) -> Check:
    return lambda v: v in values


def nullable(check: Check) -> Check:
    return lambda v: v is None or check(v)


def json_list(max_items: int, item: Check | None = None) -> Check:
    def check(v: Any) -> bool:
        if not isinstance(v, list) or len(v) > max_items:
            return False
        if item is not None and not all(item(x) for x in v):
            return False
        return len(json.dumps(v, ensure_ascii=False)) <= MAX_JSON_FIELD
    return check


def _example(v: Any) -> bool:
    return (isinstance(v, dict) and set(v) == {"ru", "uz"}
            and all(isinstance(v[k], str) and len(v[k]) <= 1000 for k in ("ru", "uz")))


BASE: dict[str, Check] = {
    "id": _uuid,
    "created_at": _timestamp,
    "updated_at": _timestamp,
    "deleted_at": nullable(_timestamp),
    "version": integer(1),
}

SPECS: dict[str, dict[str, Check]] = {
    "user_vocabulary": {
        "lexeme_id": text(1, 200),
        "lemma": text(1, 200),
        "pos": nullable(text(0, 50)),
        "translation": text(0, 200),
        "note": text(0, 5000),
        "examples": json_list(50, _example),
        "status": one_of("learning", "known"),
    },
    "flashcards": {
        "lexeme_id": text(1, 200),
        "direction": one_of("ru_uz", "uz_ru"),
        "due_at": _timestamp,
        "interval_days": number(0, 100_000),
        "ease": number(0, 10),
        "reps": integer(0),
        "lapses": integer(0),
        "last_review_at": nullable(_timestamp),
    },
    "review_history": {
        "card_id": _uuid,
        "reviewed_at": _timestamp,
        "grade": integer(0, 3),
        "interval_after": number(0, 100_000),
        "ease_after": number(0, 10),
    },
    "reading_texts": {
        "title": text(1, 200),
        "body": text(1, 50_000),
        "source": text(0, 1000),
    },
    "reading_history": {
        "text_id": _uuid,
        "read_at": _timestamp,
        "words": integer(0),
        "looked_up": integer(0),
        "duration_ms": integer(0),
    },
    "test_results": {
        "kind": text(1, 50),
        "taken_at": _timestamp,
        "total": integer(0),
        "correct": integer(0),
        "details": json_list(500),
    },
}
TABLES = tuple(SPECS)


def check_row(table: str, row: Any) -> dict[str, Any]:
    """The row if it follows the table's rules, otherwise RowError with the reason."""
    if not isinstance(row, dict):
        raise RowError("invalid_row")
    spec = {**BASE, **SPECS[table]}
    if set(row) != set(spec):
        raise RowError("invalid_fields")
    for field, check in spec.items():
        if not check(row[field]):
            raise RowError(f"invalid_{field}")
    if table == "test_results" and row["correct"] > row["total"]:
        raise RowError("invalid_correct")
    row = dict(row)
    row["id"] = str(uuid.UUID(row["id"]))
    return row


def _newer(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return (a["version"], datetime.fromisoformat(a["updated_at"])) > (b["version"], datetime.fromisoformat(b["updated_at"]))


def parse_push(body: dict[str, Any]) -> tuple[list[tuple[str, dict[str, Any]]], list[dict[str, str]]]:
    """Valid rows (one per table and id, the newest kept) and the refused ones."""
    changes = body.get("changes")
    if not isinstance(changes, list):
        raise bad_request("invalid_changes", "changes must be a list")
    if len(changes) > MAX_PUSH_ROWS:
        raise bad_request("too_many_changes", f"send at most {MAX_PUSH_ROWS} changes at a time")
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    rejected: list[dict[str, str]] = []
    for change in changes:
        table = change.get("table") if isinstance(change, dict) else None
        raw = change.get("row") if isinstance(change, dict) else None
        raw_id = raw.get("id") if isinstance(raw, dict) and isinstance(raw.get("id"), str) else ""
        if table not in SPECS:
            rejected.append({"table": str(table)[:50], "id": raw_id[:50], "code": "invalid_table"})
            continue
        try:
            row = check_row(table, raw)
        except RowError as exc:
            rejected.append({"table": table, "id": raw_id[:50], "code": exc.code})
            continue
        key = (table, row["id"])
        if key not in rows or _newer(row, rows[key]):
            rows[key] = row
    return [(table, row) for (table, _), row in rows.items()], rejected


async def touch_device(conn, user_id: str, device_id: str, now: datetime, *, synced: bool) -> None:
    """Marks the device as seen. A device that was signed out (no live session) is refused."""
    found = await conn.fetchval(
        """
        UPDATE devices SET last_seen_at = $3, last_sync_at = CASE WHEN $4 THEN $3 ELSE last_sync_at END
        WHERE id = $1 AND user_id = $2
          AND EXISTS (SELECT 1 FROM refresh_tokens t
                      WHERE t.device_id = devices.id AND t.revoked_at IS NULL AND t.expires_at > $3)
        RETURNING id
        """,
        uuid.UUID(device_id), uuid.UUID(user_id), now, synced,
    )
    if found is None:
        raise unauthorized("this device was signed out")


async def push(conn, *, user_id: str, device_id: str, body: dict[str, Any], now: datetime) -> dict[str, Any]:
    rows, rejected = parse_push(body)
    accepted: list[dict[str, str]] = []
    conflicts: list[dict[str, Any]] = []
    async with conn.transaction():
        await touch_device(conn, user_id, device_id, now, synced=False)
        # One push at a time per user, so server_seq values become visible in order.
        await conn.execute("SELECT 1 FROM users WHERE id = $1 FOR UPDATE", uuid.UUID(user_id))
        if rows:
            written = await conn.fetch(
                """
                INSERT INTO sync_records AS s (user_id, tbl, id, data, version, updated_at, deleted_at, device_id)
                SELECT $1, t.tbl, t.id::uuid, t.data::jsonb, t.version, t.updated_at::timestamptz,
                       t.deleted_at::timestamptz, $2
                FROM unnest($3::text[], $4::text[], $5::text[], $6::int[], $7::text[], $8::text[])
                     AS t(tbl, id, data, version, updated_at, deleted_at)
                ON CONFLICT (user_id, tbl, id) DO UPDATE
                SET data = EXCLUDED.data, version = EXCLUDED.version, updated_at = EXCLUDED.updated_at,
                    deleted_at = EXCLUDED.deleted_at, device_id = EXCLUDED.device_id,
                    server_seq = nextval('sync_seq'), received_at = now()
                WHERE (EXCLUDED.version, EXCLUDED.updated_at) > (s.version, s.updated_at)
                RETURNING tbl, id::text AS id
                """,
                uuid.UUID(user_id), uuid.UUID(device_id),
                [t for t, _ in rows], [r["id"] for _, r in rows],
                [json.dumps(r, ensure_ascii=False) for _, r in rows], [r["version"] for _, r in rows],
                [r["updated_at"] for _, r in rows], [r["deleted_at"] for _, r in rows],
            )
            done = {(w["tbl"], w["id"]) for w in written}
            accepted = [{"table": t, "id": r["id"]} for t, r in rows if (t, r["id"]) in done]
            stale = [(t, r["id"]) for t, r in rows if (t, r["id"]) not in done]
            if stale:
                current = await conn.fetch(
                    """
                    SELECT s.tbl, s.data::text AS data FROM sync_records s
                    JOIN unnest($2::text[], $3::uuid[]) AS k(tbl, id) ON s.tbl = k.tbl AND s.id = k.id
                    WHERE s.user_id = $1
                    """,
                    uuid.UUID(user_id), [t for t, _ in stale], [uuid.UUID(i) for _, i in stale],
                )
                conflicts = [{"table": c["tbl"], "row": json.loads(c["data"])} for c in current]
    return {"accepted": accepted, "conflicts": conflicts, "rejected": rejected}


def parse_since(value: str | None) -> int:
    if value is None or value == "":
        return 0
    if not value.isdigit() or len(value) > 19:
        raise bad_request("invalid_since", "since must be a non-negative integer")
    return int(value)


async def pull(conn, *, user_id: str, device_id: str, since: int, now: datetime) -> dict[str, Any]:
    await touch_device(conn, user_id, device_id, now, synced=True)
    rows = await conn.fetch(
        """
        SELECT tbl, data::text AS data, server_seq FROM sync_records
        WHERE user_id = $1 AND server_seq > $2
        ORDER BY server_seq
        LIMIT $3
        """,
        uuid.UUID(user_id), since, PULL_LIMIT + 1,
    )
    more = len(rows) > PULL_LIMIT
    rows = rows[:PULL_LIMIT]
    return {
        "changes": [{"table": r["tbl"], "row": json.loads(r["data"])} for r in rows],
        "cursor": rows[-1]["server_seq"] if rows else since,
        "more": more,
    }


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


async def account(conn, *, user_id: str, device_id: str, now: datetime) -> dict[str, Any]:
    """The account overview: what the account holds and the devices that used it."""
    uid = uuid.UUID(user_id)
    counts = await conn.fetchrow(
        """
        SELECT
          count(*) FILTER (WHERE tbl = 'user_vocabulary') AS words,
          count(*) FILTER (WHERE tbl = 'user_vocabulary' AND data->>'status' = 'known') AS known_words,
          count(*) FILTER (WHERE tbl = 'flashcards') AS cards,
          count(*) FILTER (WHERE tbl = 'review_history') AS reviews,
          count(*) FILTER (WHERE tbl = 'reading_texts') AS texts,
          count(*) FILTER (WHERE tbl = 'reading_history') AS readings,
          count(*) FILTER (WHERE tbl = 'test_results') AS tests,
          max(received_at) AS last_change_at
        FROM sync_records WHERE user_id = $1 AND deleted_at IS NULL
        """,
        uid,
    )
    devices = await conn.fetch(
        """
        SELECT d.id, d.name, d.platform, d.created_at, d.last_seen_at, d.last_sync_at,
               EXISTS (SELECT 1 FROM refresh_tokens t
                       WHERE t.device_id = d.id AND t.revoked_at IS NULL AND t.expires_at > $2) AS signed_in
        FROM devices d WHERE d.user_id = $1
        ORDER BY d.last_seen_at DESC
        """,
        uid, now,
    )
    progress = {k: counts[k] for k in ("words", "known_words", "cards", "reviews", "texts", "readings", "tests")}
    progress["last_change_at"] = _iso(counts["last_change_at"])
    return {
        "progress": progress,
        "devices": [
            {
                "id": str(d["id"]),
                "name": d["name"],
                "platform": d["platform"],
                "created_at": _iso(d["created_at"]),
                "last_seen_at": _iso(d["last_seen_at"]),
                "last_sync_at": _iso(d["last_sync_at"]),
                "signed_in": d["signed_in"],
                "current": str(d["id"]) == device_id,
            }
            for d in devices
        ],
    }


async def revoke_device(conn, *, user_id: str, current_device_id: str, target: Any, now: datetime,
                        ip: str | None, audit) -> None:
    """Signs the account out on another device: all of its sessions end."""
    if not _uuid(target):
        raise bad_request("invalid_device", "device_id must be a UUID")
    target_id = str(uuid.UUID(target))
    if target_id == current_device_id:
        raise bad_request("current_device", "use sign out for this device")
    async with conn.transaction():
        owned = await conn.fetchval(
            "SELECT 1 FROM devices WHERE id = $1 AND user_id = $2", uuid.UUID(target_id), uuid.UUID(user_id),
        )
        if not owned:
            raise ApiError(404, "device_not_found", "no such device on this account")
        await conn.execute(
            "UPDATE refresh_tokens SET revoked_at = $2 WHERE device_id = $1 AND revoked_at IS NULL",
            uuid.UUID(target_id), now,
        )
        await audit(conn, "device_revoked", user_id=uuid.UUID(user_id), device_id=uuid.UUID(current_device_id),
                    ip=ip, target=target_id)
