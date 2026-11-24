-- Central database (PostgreSQL), migration 3: word translations shared by every device.
-- The admin writes them in the app's admin panel (POST /v1/translations, admin accounts only);
-- every app reads them without an account (GET /v1/translations) and keeps a copy for offline use.
-- One row per lexeme (the engine's stable lexeme id). A removal is a mark (deleted_at), so it
-- reaches the devices too. The newer updated_at wins; server_seq is the pull cursor.

CREATE SEQUENCE translation_seq AS bigint;

CREATE TABLE translations (
    lexeme_id   text PRIMARY KEY CHECK (length(lexeme_id) BETWEEN 1 AND 200),
    lemma       text NOT NULL CHECK (length(lemma) BETWEEN 1 AND 200),
    translation text NOT NULL CHECK (length(translation) <= 200),
    updated_at  timestamptz NOT NULL,            -- when the admin made the change (device clock)
    deleted_at  timestamptz,
    server_seq  bigint NOT NULL DEFAULT nextval('translation_seq'),
    updated_by  uuid REFERENCES users (id) ON DELETE SET NULL,
    received_at timestamptz NOT NULL DEFAULT now(),
    CHECK (deleted_at IS NOT NULL OR length(translation) >= 1)
);
CREATE INDEX translations_seq_idx ON translations (server_seq);
