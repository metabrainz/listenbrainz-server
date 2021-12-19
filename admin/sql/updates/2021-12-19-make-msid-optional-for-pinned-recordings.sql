BEGIN;

ALTER TABLE pinned_recording ALTER COLUMN recording_msid DROP NOT NULL;

ALTER TABLE pinned_recording
    ADD CONSTRAINT recording_msid_or_recording_mbid_check
    CHECK ( recording_msid IS NOT NULL OR recording_mbid IS NOT NULL );

COMMIT;
