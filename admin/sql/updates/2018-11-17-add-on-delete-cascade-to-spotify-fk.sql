BEGIN;

ALTER TABLE spotify_auth
    DROP CONSTRAINT spotify_auth_user_id_foreign_key;

ALTER TABLE spotify_auth
    ADD CONSTRAINT spotify_auth_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

COMMIT;
