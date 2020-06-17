BEGIN;

ALTER TABLE statistics.user ADD COLUMN listening_activity JSONB;

COMMIT;
