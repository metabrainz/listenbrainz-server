BEGIN;

ALTER TABLE recording_feedback ALTER COLUMN recording_msid DROP NOT NULL;

ALTER TABLE recording_feedback ADD COLUMN recording_mbid UUID;

ALTER TABLE recording_feedback
    ADD CONSTRAINT feedback_recording_msid_or_recording_mbid_check
    CHECK ( recording_msid IS NOT NULL OR recording_mbid IS NOT NULL );

CREATE UNIQUE INDEX user_id_mbid_ndx_rec_feedback ON recording_feedback (user_id, recording_mbid);

COMMIT;
