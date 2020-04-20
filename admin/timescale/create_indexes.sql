BEGIN;

CREATE INDEX listened_at_user_name_ndx_listen ON listen (listened_at DESC, user_name);
CREATE UNIQUE INDEX listened_at_recording_msid_user_name_ndx_listen ON listen (listened_at DESC, recording_msid, user_name);

COMMIT;
