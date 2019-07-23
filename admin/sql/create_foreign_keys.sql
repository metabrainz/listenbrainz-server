BEGIN;

ALTER TABLE api_compat.token
    ADD CONSTRAINT token_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

ALTER TABLE api_compat.session
    ADD CONSTRAINT session_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

ALTER TABLE statistics.user
    ADD CONSTRAINT user_stats_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

ALTER TABLE spotify_auth
    ADD CONSTRAINT spotify_auth_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

ALTER TABLE follow_list
    ADD CONSTRAINT follow_list_user_id_foreign_key
    FOREIGN KEY (creator)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

ALTER TABLE recommendation.cf_recording
    ADD CONSTRAINT cf_recording_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

ALTER TABLE recommendation.cf_recording_recommender_join
    ADD CONSTRAINT cf_recording_recommender_join_recommender_id_foreign_key
    FOREIGN KEY (recommender_id)
    REFERENCES recommendation.recommender (id)
    ON DELETE CASCADE;

ALTER TABLE recommendation.cf_recording_recommender_join
    ADD CONSTRAINT cf_recording_recommender_join_cf_recording_id_foreign_key
    FOREIGN KEY (cf_recording_id)
    REFERENCES recommendation.cf_recording (id)
    ON DELETE CASCADE;

COMMIT;
