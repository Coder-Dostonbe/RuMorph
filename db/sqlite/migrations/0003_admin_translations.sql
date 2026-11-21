-- Device database (SQLite), migration 3: word translations entered in the admin panel.
-- While the app is in testing, translations are written only there; learners see a translation
-- once it exists here or in the translations file shipped with the app
-- (apps/client/src/data/translations.json, built from exports by tools/translations/merge.py).
-- One row per lexeme; removing a translation marks the row deleted, so the newer of this row and
-- the shipped entry wins. Same columns as the other synced tables (0002).
CREATE TABLE IF NOT EXISTS admin_translations (
    id          TEXT PRIMARY KEY NOT NULL,
    lexeme_id   TEXT NOT NULL CHECK (length(lexeme_id) BETWEEN 1 AND 200),
    lemma       TEXT NOT NULL,
    translation TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    deleted_at  TEXT,
    version     INTEGER NOT NULL DEFAULT 1
);
CREATE UNIQUE INDEX IF NOT EXISTS admin_translations_lexeme ON admin_translations (lexeme_id);
