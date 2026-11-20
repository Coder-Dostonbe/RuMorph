-- Device database (SQLite), migration 2: the learner's own data for the learning modules.
-- Names follow the PostgreSQL plan (docs/01-…, 6.2) so that sync (Phase 6) maps them one to one.
-- Every row has a UUID v7 id made on the device, created_at / updated_at, deleted_at (a deletion
-- is a mark, so it can be synced) and version (incremented on every change).
-- Words point at the engine's lexicon by its stable lexeme id ("книга|NOUN,inan,femn").

-- Words the learner keeps: their own translation, note and examples.
CREATE TABLE IF NOT EXISTS user_vocabulary (
    id          TEXT PRIMARY KEY NOT NULL,
    lexeme_id   TEXT NOT NULL CHECK (length(lexeme_id) BETWEEN 1 AND 200),
    lemma       TEXT NOT NULL,
    pos         TEXT,
    translation TEXT NOT NULL DEFAULT '',
    note        TEXT NOT NULL DEFAULT '',
    examples    TEXT NOT NULL DEFAULT '[]',          -- JSON array of {ru, uz}
    status      TEXT NOT NULL DEFAULT 'learning' CHECK (status IN ('learning', 'known')),
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    deleted_at  TEXT,
    version     INTEGER NOT NULL DEFAULT 1
);
CREATE UNIQUE INDEX IF NOT EXISTS user_vocabulary_lexeme ON user_vocabulary (lexeme_id) WHERE deleted_at IS NULL;

-- Spaced-repetition cards (SM-2). One card per word and direction.
CREATE TABLE IF NOT EXISTS flashcards (
    id            TEXT PRIMARY KEY NOT NULL,
    lexeme_id     TEXT NOT NULL,
    direction     TEXT NOT NULL CHECK (direction IN ('ru_uz', 'uz_ru')),
    due_at        TEXT NOT NULL,
    interval_days REAL NOT NULL DEFAULT 0,
    ease          REAL NOT NULL DEFAULT 2.5,
    reps          INTEGER NOT NULL DEFAULT 0,
    lapses        INTEGER NOT NULL DEFAULT 0,
    last_review_at TEXT,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    deleted_at    TEXT,
    version       INTEGER NOT NULL DEFAULT 1
);
CREATE UNIQUE INDEX IF NOT EXISTS flashcards_word ON flashcards (lexeme_id, direction) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS flashcards_due ON flashcards (due_at);

-- Every review, never changed (append-only).
CREATE TABLE IF NOT EXISTS review_history (
    id             TEXT PRIMARY KEY NOT NULL,
    card_id        TEXT NOT NULL,
    reviewed_at    TEXT NOT NULL,
    grade          INTEGER NOT NULL CHECK (grade BETWEEN 0 AND 3),   -- again, hard, good, easy
    interval_after REAL NOT NULL,
    ease_after     REAL NOT NULL,
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL,
    deleted_at     TEXT,
    version        INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS review_history_day ON review_history (reviewed_at);

-- Texts for reading: the learner's own (pasted) texts.
CREATE TABLE IF NOT EXISTS reading_texts (
    id         TEXT PRIMARY KEY NOT NULL,
    title      TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 200),
    body       TEXT NOT NULL CHECK (length(body) BETWEEN 1 AND 50000),
    source     TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version    INTEGER NOT NULL DEFAULT 1
);

-- Each reading session (append-only).
CREATE TABLE IF NOT EXISTS reading_history (
    id          TEXT PRIMARY KEY NOT NULL,
    text_id     TEXT NOT NULL,
    read_at     TEXT NOT NULL,
    words       INTEGER NOT NULL DEFAULT 0,
    looked_up   INTEGER NOT NULL DEFAULT 0,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    deleted_at  TEXT,
    version     INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS reading_history_day ON reading_history (read_at);

-- Each finished test (append-only).
CREATE TABLE IF NOT EXISTS test_results (
    id         TEXT PRIMARY KEY NOT NULL,
    kind       TEXT NOT NULL,
    taken_at   TEXT NOT NULL,
    total      INTEGER NOT NULL CHECK (total >= 0),
    correct    INTEGER NOT NULL CHECK (correct BETWEEN 0 AND total),
    details    TEXT NOT NULL DEFAULT '[]',           -- JSON: the questions and the answers given
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version    INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS test_results_day ON test_results (taken_at);
