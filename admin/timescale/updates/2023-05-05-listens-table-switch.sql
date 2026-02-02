BEGIN;

ALTER TABLE listen RENAME TO listen_old;
ALTER INDEX listened_at_track_name_user_id_ndx_listen RENAME TO listened_at_track_name_user_id_ndx_listen_old;
ALTER INDEX created_user_name_ndx_listen RENAME TO created_user_name_ndx_listen_old;
ALTER INDEX listen_listened_at_idx RENAME TO listen_listened_at_idx_old;
ALTER INDEX listened_at_user_id_ndx_listen RENAME TO listened_at_user_id_ndx_listen_old;

ALTER TABLE listen_new RENAME TO listen;
CREATE INDEX listened_at_user_id_ndx_listen ON listen (listened_at DESC, user_id);
CREATE INDEX created_ndx_listen ON listen (created);
CREATE UNIQUE INDEX listened_at_user_id_recording_msid_ndx_listen ON listen (listened_at DESC, user_id, recording_msid);
CREATE INDEX recording_msid_ndx_listen on listen (recording_msid);

ALTER TABLE listen_delete_metadata RENAME TO listen_delete_metadata_old;
ALTER TABLE listen_delete_metadata_new RENAME TO listen_delete_metadata;

ALTER TABLE listen_user_metadata RENAME TO listen_user_metadata_old;
ALTER INDEX user_id_ndx_user_metadata RENAME TO user_id_ndx_user_metadata_old;

ALTER TABLE listen_user_metadata_new RENAME TO listen_user_metadata;
CREATE UNIQUE INDEX user_id_ndx_listen_user_metadata ON listen_user_metadata (user_id);

COMMIT;
