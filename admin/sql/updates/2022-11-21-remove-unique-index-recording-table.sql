BEGIN;

DROP INDEX user_id_mbid_ndx_rec_feedback;
CREATE INDEX user_id_mbid_ndx_rec_feedback ON recording_feedback (user_id, recording_mbid);

COMMIT;
