-- Device database (SQLite), migration 4: rows changed on this device and not yet sent to the
-- server (the outbox of docs/01-…, 6.4). One entry per row, with the version it had when it was
-- changed; the entry goes away once the server has that version or a newer one.
-- Rows that came from the server are written without an entry.
CREATE TABLE IF NOT EXISTS sync_outbox (
    tbl     TEXT NOT NULL,
    id      TEXT NOT NULL,
    version INTEGER NOT NULL,
    PRIMARY KEY (tbl, id)
);
