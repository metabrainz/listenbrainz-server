BEGIN;

ALTER TABLE statistics.user ADD COLUMN daily_activity JSONB;

COMMIT;
