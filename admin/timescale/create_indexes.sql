BEGIN;

CREATE INDEX listened_at_user_id_ndx_listen ON listen (listened_at DESC, user_id);
CREATE INDEX created_ndx_listen ON listen (created);
CREATE UNIQUE INDEX listened_at_user_id_recording_msid_ndx_listen ON listen (listened_at DESC, user_id, recording_msid);

CREATE INDEX recording_msid_ndx_listen on listen (recording_msid);

CREATE UNIQUE INDEX user_id_ndx_listen_user_metadata ON listen_user_metadata (user_id);

-- View indexes are created in listenbrainz/db/timescale.py

COMMIT;
