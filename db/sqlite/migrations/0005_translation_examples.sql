-- Device database (SQLite), migration 5: example sentences and the "verified" mark for the
-- translations (as on the server, db/postgres/migrations/0004_translation_examples.sql).
-- examples: JSON array of {ru, uz}. verified: 1 for an admin's own entry, 0 for an unchecked draft.
ALTER TABLE admin_translations ADD COLUMN examples TEXT NOT NULL DEFAULT '[]';
ALTER TABLE admin_translations ADD COLUMN verified INTEGER NOT NULL DEFAULT 1;
