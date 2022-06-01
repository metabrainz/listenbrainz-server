BEGIN;

DROP INDEX user_id_rec_msid_ndx_feedback;
DROP INDEX user_id_mbid_ndx_rec_feedback;
DROP INDEX user_id_msid_mbid_ndx_rec_feedback;

CREATE UNIQUE INDEX user_id_msid_ndx_rec_feedback ON recording_feedback (user_id, recording_msid) WHERE recording_mbid IS NULL;
CREATE UNIQUE INDEX user_id_mbid_ndx_rec_feedback ON recording_feedback (user_id, recording_mbid) WHERE recording_msid IS NULL;
CREATE UNIQUE INDEX user_id_msid_mbid_ndx_rec_feedback ON recording_feedback (user_id, recording_msid, recording_mbid) WHERE recording_mbid IS NOT NULL AND recording_msid IS NOT NULL;

COMMIT;
