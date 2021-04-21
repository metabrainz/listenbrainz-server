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

ALTER TABLE external_service_oauth
    ADD CONSTRAINT external_service_oauth_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

ALTER TABLE recommendation.cf_recording
    ADD CONSTRAINT cf_recording_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

ALTER TABLE recommendation.recommender
    ADD CONSTRAINT recommender_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

ALTER TABLE recommendation.recording_session
    ADD CONSTRAINT recording_session_recommender_session_foreign_key
    FOREIGN KEY (session_id)
    REFERENCES recommendation.recommender_session (id)
    ON DELETE CASCADE;

ALTER TABLE recommendation.recommender_session
    ADD CONSTRAINT recommender_session_recommender_foreign_key
    FOREIGN KEY (recommender_id)
    REFERENCES recommendation.recommender (id)
    ON DELETE CASCADE;

ALTER TABLE user_timeline_event
    ADD CONSTRAINT user_timeline_event_user_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

ALTER TABLE recording_feedback
    ADD CONSTRAINT recording_feedback_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

-- NOTE: If the foreign keys for the similar_user table changes, update the code in listenbrainz/db/similar_users.py !
ALTER TABLE recommendation.similar_user
    ADD CONSTRAINT similar_user_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

ALTER TABLE missing_musicbrainz_data
    ADD CONSTRAINT missing_mb_data_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

ALTER TABLE user_relationship
    ADD CONSTRAINT user_relationship_user_0_foreign_key
    FOREIGN KEY (user_0)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

ALTER TABLE user_relationship
    ADD CONSTRAINT user_relationship_user_1_foreign_key
    FOREIGN KEY (user_1)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

ALTER TABLE recommendation_feedback
    ADD CONSTRAINT recommendation_feedback_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

COMMIT;
