-- Device database (SQLite), migration 1.
-- Holds only what the app needs offline. Names match the PostgreSQL schema
-- (db/postgres/migrations) wherever a table exists on both sides.

-- Interface and device settings: locale, theme, api_url, device_id.
-- Synced user settings (user_settings on the server) arrive in Phase 6.
CREATE TABLE IF NOT EXISTS settings (
    key        TEXT PRIMARY KEY NOT NULL CHECK (length(key) BETWEEN 1 AND 64),
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
