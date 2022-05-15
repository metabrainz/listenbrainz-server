BEGIN;

CREATE UNIQUE INDEX auth_token_ndx_user ON "user" (auth_token);
CREATE UNIQUE INDEX lower_musicbrainz_id_ndx_user ON "user" (lower(musicbrainz_id));
CREATE UNIQUE INDEX login_id_ndx_user ON "user" (login_id);

CREATE INDEX user_name_search_trgm_idx ON "user" USING GIST (musicbrainz_id gist_trgm_ops);


CREATE INDEX reporter_user_id_ndx_reported_users ON reported_users (reporter_user_id);
CREATE INDEX reported_user_id_ndx_reported_users ON reported_users (reported_user_id);
CREATE UNIQUE INDEX user_id_reports_ndx_reported_users ON reported_users (reporter_user_id, reported_user_id);

CREATE UNIQUE INDEX token_ndx_token ON api_compat.token (token);
CREATE UNIQUE INDEX token_api_key_ndx_token ON api_compat.token (token, api_key);

CREATE UNIQUE INDEX sid_ndx_session ON api_compat.session (sid);
CREATE UNIQUE INDEX sid_api_key_ndx_session ON api_compat.session (sid, api_key);

CREATE UNIQUE INDEX msid_ndx_artist_stats ON statistics.artist (msid);
CREATE UNIQUE INDEX msid_ndx_release_stats ON statistics.release (msid);
CREATE UNIQUE INDEX msid_ndx_recording_stats ON statistics.recording (msid);

CREATE UNIQUE INDEX user_type_range_ndx_stats ON statistics.user (user_id, stats_type, stats_range);
CREATE INDEX user_id_ndx__user_stats ON statistics.user (user_id);

CREATE INDEX latest_listened_at_spotify_auth ON spotify_auth (latest_listened_at DESC NULLS LAST);

CREATE INDEX user_id_ndx_external_service_oauth ON external_service_oauth (user_id);
CREATE INDEX service_ndx_external_service_oauth ON external_service_oauth (service);
CREATE UNIQUE INDEX user_id_service_ndx_external_service_oauth ON external_service_oauth (user_id, service);

CREATE INDEX user_id_ndx_listens_importer ON listens_importer (user_id);
CREATE INDEX service_ndx_listens_importer ON listens_importer (service);
CREATE UNIQUE INDEX user_id_service_ndx_listens_importer ON listens_importer (user_id, service);
CREATE INDEX latest_listened_at_ndx_listens_importer ON listens_importer (latest_listened_at DESC NULLS LAST);

CREATE UNIQUE INDEX user_id_rec_msid_ndx_feedback ON recording_feedback (user_id, recording_msid);
CREATE UNIQUE INDEX user_id_mbid_ndx_rec_feedback ON recording_feedback (user_id, recording_mbid);

-- NOTE: If the indexes for the similar_user table changes, update the code in listenbrainz/db/similar_users.py !
CREATE UNIQUE INDEX user_id_ndx_similar_user ON recommendation.similar_user (user_id);

CREATE INDEX user_0_user_relationship_ndx ON user_relationship (user_0);
CREATE INDEX user_1_user_relationship_ndx ON user_relationship (user_1);

CREATE UNIQUE INDEX user_id_rec_mbid_ndx_feedback ON recommendation_feedback (user_id, recording_mbid);

CREATE INDEX rating_recommendation_feedback ON recommendation_feedback (rating);

CREATE INDEX user_id_ndx_user_timeline_event ON user_timeline_event (user_id);
CREATE INDEX event_type_ndx_user_timeline_event ON user_timeline_event (event_type);
CREATE INDEX user_id_event_type_ndx_user_timeline_event ON user_timeline_event (user_id, event_type);

CREATE UNIQUE INDEX user_id_event_type_event_id_ndx_hide_user_timeline_event ON hide_user_timeline_event (user_id, event_type, event_id);

CREATE INDEX user_id_ndx_pinned_recording ON pinned_recording (user_id);

CREATE INDEX release_mbid_ndx_release_color ON release_color (release_mbid);
CREATE UNIQUE INDEX caa_id_ndx_release_color ON release_color (caa_id);

COMMIT;
