BEGIN;

ALTER TABLE recording_feedback ALTER COLUMN recording_msid DROP NOT NULL;

ALTER TABLE recording_feedback ADD COLUMN recording_mbid UUID;

ALTER TABLE recording_feedback
    ADD CONSTRAINT feedback_recording_msid_or_recording_mbid_check
    CHECK ( recording_msid IS NOT NULL OR recording_mbid IS NOT NULL );

COMMIT;
