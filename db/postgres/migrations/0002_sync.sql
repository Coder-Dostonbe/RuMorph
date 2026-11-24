-- Central database (PostgreSQL), migration 2: the learner's data synced between devices.
--
-- One row per record of a device table (db/sqlite/migrations/0002_learning.sql). `data` is the
-- whole row as the device stores it; the API checks every field before it is written
-- (apps/api/src/tilsim_api/sync.py). version / updated_at / deleted_at are copied out of `data`
-- for the conflict rule: the higher (version, updated_at) wins.
--
-- server_seq is the pull cursor: every write takes the next value. Writes of one user are
-- serialised (sync.push locks the user's row), so a user's rows become visible in server_seq
-- order and a pull never skips one.

CREATE SEQUENCE sync_seq AS bigint;

CREATE TABLE sync_records (
    user_id     uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    tbl         text NOT NULL CHECK (tbl IN ('user_vocabulary', 'flashcards', 'review_history',
                                             'reading_texts', 'reading_history', 'test_results')),
    id          uuid NOT NULL,
    data        jsonb NOT NULL,
    version     integer NOT NULL CHECK (version >= 1),
    updated_at  timestamptz NOT NULL,            -- device clock; only breaks ties between equal versions
    deleted_at  timestamptz,
    server_seq  bigint NOT NULL DEFAULT nextval('sync_seq'),
    device_id   uuid REFERENCES devices (id) ON DELETE SET NULL,
    received_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, tbl, id)
);
CREATE INDEX sync_records_user_seq_idx ON sync_records (user_id, server_seq);

-- When the device last finished a sync (shown in the account's device list).
ALTER TABLE devices ADD COLUMN last_sync_at timestamptz;

-- For the checks "does this device still have a live session" (sync, account) and the limit
-- on new accounts per network address (auth.register).
CREATE INDEX refresh_tokens_device_idx ON refresh_tokens (device_id);
CREATE INDEX audit_log_action_ip_time_idx ON audit_log (action, ip, created_at DESC);
