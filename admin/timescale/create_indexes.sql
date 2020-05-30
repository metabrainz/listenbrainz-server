BEGIN;

CREATE INDEX listened_at_user_name_ndx_listen ON listen (listened_at DESC, user_name);
CREATE UNIQUE INDEX listened_at_track_name_user_name_ndx_listen ON listen (listened_at DESC, track_name, user_name);

COMMIT;
