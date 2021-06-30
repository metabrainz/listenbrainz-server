BEGIN;

-- Changes: recording_mbid column is now optional
-- added a required recording_msid column,

ALTER TABLE pinned_recording
ALTER COLUMN recording_mbid DROP NOT NULL,
ADD COLUMN recording_msid UUID NOT NULL;

COMMIT;