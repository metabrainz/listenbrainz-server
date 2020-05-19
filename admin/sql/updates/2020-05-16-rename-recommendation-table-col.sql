BEGIN;

ALTER TABLE recommendation.cf_recording
RENAME COLUMN recording_msid TO recording_mbid;

COMMIT;
