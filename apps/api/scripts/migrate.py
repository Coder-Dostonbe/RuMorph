"""Applies db/postgres/migrations/*.sql to a PostgreSQL database, in order, once each.

Usage (from apps/api):
    DATABASE_URL="postgres://..." uv run python scripts/migrate.py
    DATABASE_URL="postgres://..." uv run python scripts/migrate.py --status

Use Neon's direct (non-pooled) connection string for migrations. Each file runs
in its own transaction together with its schema_migrations row.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import sys
from pathlib import Path

import asyncpg

MIGRATIONS = Path(__file__).resolve().parents[3] / "db" / "postgres" / "migrations"


def migration_files() -> list[Path]:
    files = sorted(MIGRATIONS.glob("[0-9][0-9][0-9][0-9]_*.sql"))
    numbers = [int(f.name[:4]) for f in files]
    if numbers != list(range(1, len(files) + 1)):
        raise SystemExit(f"migrations must be numbered 0001, 0002, … without gaps: {[f.name for f in files]}")
    return files


async def migrate(url: str, status_only: bool = False) -> list[str]:
    conn = await asyncpg.connect(url)
    try:
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS schema_migrations (
                   version integer PRIMARY KEY,
                   name text NOT NULL,
                   sha256 text NOT NULL,
                   applied_at timestamptz NOT NULL DEFAULT now())"""
        )
        applied = {r["version"]: r for r in await conn.fetch("SELECT version, name, sha256 FROM schema_migrations")}
        done: list[str] = []
        for path in migration_files():
            version = int(path.name[:4])
            sql = path.read_text(encoding="utf-8")
            digest = hashlib.sha256(sql.encode("utf-8")).hexdigest()
            if version in applied:
                if applied[version]["sha256"] != digest:
                    raise SystemExit(f"{path.name} changed after it was applied; add a new migration instead")
                continue
            if status_only:
                print(f"pending: {path.name}")
                continue
            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute(
                    "INSERT INTO schema_migrations (version, name, sha256) VALUES ($1, $2, $3)",
                    version, path.name, digest,
                )
            done.append(path.name)
            print(f"applied: {path.name}")
        if not done and not status_only:
            print("database is up to date")
        return done
    finally:
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--status", action="store_true", help="list pending migrations without applying them")
    args = parser.parse_args()
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("set DATABASE_URL to the PostgreSQL connection string")
    asyncio.run(migrate(url, status_only=args.status))


if __name__ == "__main__":
    main()
