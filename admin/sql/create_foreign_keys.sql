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

ALTER TABLE follow_list_member
    ADD CONSTRAINT follow_list_member_list_id_foreign_key
    FOREIGN KEY (list_id)
    REFERENCES follow_list (id)
    ON DELETE CASCADE;

ALTER TABLE follow_list_member
    ADD CONSTRAINT follow_list_member_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

COMMIT;
