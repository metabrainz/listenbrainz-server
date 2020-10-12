BEGIN;

CREATE UNIQUE INDEX auth_token_ndx_user ON "user" (auth_token);
CREATE UNIQUE INDEX lower_musicbrainz_id_ndx_user ON "user" (lower(musicbrainz_id));
CREATE UNIQUE INDEX login_id_ndx_user ON "user" (login_id);

CREATE UNIQUE INDEX token_ndx_token ON api_compat.token (token);
CREATE UNIQUE INDEX token_api_key_ndx_token ON api_compat.token (token, api_key);

CREATE UNIQUE INDEX sid_ndx_session ON api_compat.session (sid);
CREATE UNIQUE INDEX sid_api_key_ndx_session ON api_compat.session (sid, api_key);

CREATE UNIQUE INDEX user_id_ndx_user_stats ON statistics.user (user_id);
CREATE UNIQUE INDEX msid_ndx_artist_stats ON statistics.artist (msid);
CREATE UNIQUE INDEX msid_ndx_release_stats ON statistics.release (msid);
CREATE UNIQUE INDEX msid_ndx_recording_stats ON statistics.recording (msid);

CREATE INDEX latest_listened_at_spotify_auth ON spotify_auth (latest_listened_at DESC NULLS LAST);

CREATE INDEX creator_ndx_follow_list ON follow_list (creator);
CREATE INDEX last_saved_ndx_follow_list ON follow_list (last_saved DESC);

CREATE UNIQUE INDEX user_id_rec_msid_ndx_feedback ON recording_feedback (user_id, recording_msid);

CREATE INDEX user_0_user_relationship_ndx ON user_relationship (user_0);
CREATE INDEX user_1_user_relationship_ndx ON user_relationship (user_1);

CREATE UNIQUE INDEX user_id_rec_mbid_ndx_feedback ON recommendation_feedback (user_id, recording_mbid);

CREATE INDEX rating_recommendation_feedback ON recommendation_feedback (rating);

COMMIT;
