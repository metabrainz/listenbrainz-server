BEGIN;

ALTER TABLE "user" ADD CONSTRAINT user_pkey PRIMARY KEY (id);
ALTER TABLE api_compat.session ADD CONSTRAINT session_pkey PRIMARY KEY (sid);
ALTER TABLE spotify_auth ADD CONSTRAINT spotify_auth_pkey PRIMARY KEY (user_id);
ALTER TABLE external_service_oauth ADD CONSTRAINT external_service_oauth_pkey PRIMARY KEY (id);
ALTER TABLE listens_importer ADD CONSTRAINT listens_importer_pkey PRIMARY KEY (id);

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

ALTER TABLE user_setting ADD CONSTRAINT user_setting_pkey PRIMARY KEY (id);

ALTER TABLE recommendation.do_not_recommend ADD CONSTRAINT rec_do_not_recommend_pkey PRIMARY KEY (id);

ALTER TABLE background_tasks ADD CONSTRAINT background_tasks_id_pkey PRIMARY KEY (id);

ALTER TABLE user_data_export ADD CONSTRAINT user_data_export_id_pkey PRIMARY KEY (id);

COMMIT;
