BEGIN;

CREATE UNIQUE INDEX auth_token_ndx_user ON "user" (auth_token);
CREATE UNIQUE INDEX lower_musicbrainz_id_ndx_user ON "user" (lower(musicbrainz_id));

CREATE UNIQUE INDEX user_id_ts_ndx_listen ON listen (user_id, ts);
CREATE INDEX user_id_ndx_listen ON listen (user_id);
CREATE INDEX ts_ndx_listen ON listen (ts);

CREATE UNIQUE INDEX token_ndx_token ON api_compat.token (token);
CREATE UNIQUE INDEX token_api_key_ndx_token ON api_compat.token (token, api_key);

CREATE UNIQUE INDEX sid_ndx_session ON api_compat.session (sid);
CREATE UNIQUE INDEX sid_api_key_ndx_session ON api_compat.session (sid, api_key);

CREATE UNIQUE INDEX id_listen_json ON "listen_json" (id);

CREATE UNIQUE INDEX user_id_ndx_user_stats ON statistics.user (user_id);
CREATE UNIQUE INDEX msid_ndx_artist_stats ON statistics.artist (msid);
CREATE UNIQUE INDEX msid_ndx_release_stats ON statistics.release (msid);
CREATE UNIQUE INDEX msid_ndx_recording_stats ON statistics.recording (msid);

COMMIT;
