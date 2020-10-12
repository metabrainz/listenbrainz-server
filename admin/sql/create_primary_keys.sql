BEGIN;

ALTER TABLE "user" ADD CONSTRAINT user_pkey PRIMARY KEY (id);
ALTER TABLE api_compat.session ADD CONSTRAINT session_pkey PRIMARY KEY (sid);
ALTER TABLE spotify_auth ADD CONSTRAINT spotify_auth_pkey PRIMARY KEY (user_id);
ALTER TABLE follow_list ADD CONSTRAINT follow_list_pkey PRIMARY KEY (id);

ALTER TABLE statistics.user ADD CONSTRAINT stats_user_pkey PRIMARY KEY (user_id);
ALTER TABLE statistics.artist ADD CONSTRAINT stats_artist_pkey PRIMARY KEY (id);
ALTER TABLE statistics.release ADD CONSTRAINT stats_release_pkey PRIMARY KEY (id);
ALTER TABLE statistics.recording ADD CONSTRAINT stats_recording_pkey PRIMARY KEY (id);

ALTER TABLE recommendation.cf_recording ADD CONSTRAINT rec_cf_recording_pkey PRIMARY KEY (id);
ALTER TABLE recommendation.recommender ADD CONSTRAINT rec_recommender_pkey PRIMARY KEY (id);
ALTER TABLE recommendation.recommender_session ADD CONSTRAINT rec_recommender_session_pkey PRIMARY KEY (id);

ALTER TABLE recording_feedback ADD CONSTRAINT recording_feedback_pkey PRIMARY KEY (id);

ALTER TABLE missing_musicbrainz_data ADD CONSTRAINT missing_mb_data_pkey PRIMARY KEY (id);

ALTER TABLE user_relationship ADD CONSTRAINT user_relationship_pkey PRIMARY KEY (user_0, user_1, relationship_type);

ALTER TABLE recommendation_feedback ADD CONSTRAINT recommendation_feedback_pkey PRIMARY KEY (id);

COMMIT;
