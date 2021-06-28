-- we use this script when we need to log out all users.
-- see https://flask-login.readthedocs.io/en/latest/#alternative-tokens for how/why it works
BEGIN;
UPDATE "user"
    SET login_id = uuid_generate_v4()::text;
COMMIT;
