CREATE UNIQUE INDEX listened_at_user_id_track_name_ndx_listen ON listen (listened_at DESC, user_id, LOWER(track_name));

DROP INDEX listened_at_track_name_user_id_ndx_listen;
