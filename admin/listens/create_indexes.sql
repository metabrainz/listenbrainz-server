BEGIN;

CREATE UNIQUE INDEX user_id_listened_at_recording_msid_ndx_listen ON listen (user_id, listened_at DESC, recording_msid);
CREATE INDEX created_ndx_listen ON listen (created);

CREATE INDEX IF NOT EXISTS listen_delete_metadata_pending_idx ON listen_delete_metadata (id) WHERE status = 'pending';

COMMIT;
