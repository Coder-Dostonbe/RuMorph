-- Central database (PostgreSQL), migration 4: example sentences and the "verified" mark for the
-- shared translations. examples: up to 3 {ru, uz} pairs. verified: false for a draft nobody has
-- checked yet (the app shows a "not checked" mark); an admin's own edit is verified.
ALTER TABLE translations ADD COLUMN examples jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE translations ADD COLUMN verified boolean NOT NULL DEFAULT true;
