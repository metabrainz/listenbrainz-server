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

COMMIT;
