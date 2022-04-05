BEGIN;

ALTER TABLE "user" ADD CONSTRAINT user_pkey PRIMARY KEY (id);
ALTER TABLE api_compat.session ADD CONSTRAINT session_pkey PRIMARY KEY (sid);
ALTER TABLE spotify_auth ADD CONSTRAINT spotify_auth_pkey PRIMARY KEY (user_id);
ALTER TABLE external_service_oauth ADD CONSTRAINT external_service_oauth_pkey PRIMARY KEY (id);
ALTER TABLE listens_importer ADD CONSTRAINT listens_importer_pkey PRIMARY KEY (id);

ALTER TABLE statistics.artist ADD CONSTRAINT stats_artist_pkey PRIMARY KEY (id);
ALTER TABLE statistics.release ADD CONSTRAINT stats_release_pkey PRIMARY KEY (id);
ALTER TABLE statistics.recording ADD CONSTRAINT stats_recording_pkey PRIMARY KEY (id);
ALTER TABLE statistics.user ADD CONSTRAINT stats_user_pkey PRIMARY KEY (id);
ALTER TABLE statistics.year_in_music ADD CONSTRAINT stats_year_in_music_pkey PRIMARY KEY (user_id);

ALTER TABLE recommendation.cf_recording ADD CONSTRAINT rec_cf_recording_pkey PRIMARY KEY (id);
ALTER TABLE recommendation.recommender ADD CONSTRAINT rec_recommender_pkey PRIMARY KEY (id);
ALTER TABLE recommendation.recommender_session ADD CONSTRAINT rec_recommender_session_pkey PRIMARY KEY (id);

ALTER TABLE user_timeline_event ADD CONSTRAINT user_timeline_event_pkey PRIMARY KEY (id);

ALTER TABLE hide_user_timeline_event ADD CONSTRAINT hide_user_timeline_event_pkey PRIMARY KEY (id);

ALTER TABLE recording_feedback ADD CONSTRAINT recording_feedback_pkey PRIMARY KEY (id);

ALTER TABLE missing_musicbrainz_data ADD CONSTRAINT missing_mb_data_pkey PRIMARY KEY (id);

ALTER TABLE user_relationship ADD CONSTRAINT user_relationship_pkey PRIMARY KEY (user_0, user_1, relationship_type);

ALTER TABLE recommendation_feedback ADD CONSTRAINT recommendation_feedback_pkey PRIMARY KEY (id);

ALTER TABLE pinned_recording ADD CONSTRAINT pinned_recording_pkey PRIMARY KEY (id);

ALTER TABLE release_color ADD CONSTRAINT release_color_pkey PRIMARY KEY (id);

COMMIT;
