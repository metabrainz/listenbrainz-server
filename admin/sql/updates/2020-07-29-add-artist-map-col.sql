BEGIN;

ALTER TABLE statistics.user ADD COLUMN artist_map JSONB;

COMMIT;
