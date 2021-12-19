BEGIN;

ALTER TABLE pinned_recording ALTER COLUMN recording_msid DROP NOT NULL;

COMMIT;
