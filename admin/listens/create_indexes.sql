BEGIN;

CREATE UNIQUE INDEX user_id_listened_at_recording_msid_ndx_listen ON listen (user_id, listened_at DESC, recording_msid);
CREATE INDEX created_ndx_listen ON listen (created);

COMMIT;
