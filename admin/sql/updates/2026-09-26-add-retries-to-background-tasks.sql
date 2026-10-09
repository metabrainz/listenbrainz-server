BEGIN;

ALTER TABLE background_tasks ADD COLUMN retries INTEGER NOT NULL DEFAULT 0;
ALTER TABLE background_tasks ADD COLUMN last_error TEXT;

COMMIT;
