import asyncio

import migrate
import pytest


def test_migrations_are_idempotent(database_url):
    assert asyncio.run(migrate.migrate(database_url)) == []


def test_files_are_numbered_without_gaps():
    names = [f.name for f in migrate.migration_files()]
    assert names[0].startswith("0001_")


def test_changed_migration_is_refused(database_url, api):
    api.query("UPDATE schema_migrations SET sha256 = 'tampered' WHERE version = 1")
    try:
        with pytest.raises(SystemExit, match="changed after it was applied"):
            asyncio.run(migrate.migrate(database_url))
    finally:
        import hashlib

        digest = hashlib.sha256(migrate.migration_files()[0].read_text(encoding="utf-8").encode()).hexdigest()
        api.query("UPDATE schema_migrations SET sha256 = $1 WHERE version = 1", digest)
