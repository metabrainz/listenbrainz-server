BEGIN;

-- Add column for alternative user id for login purpose to user table
ALTER TABLE "user" ADD COLUMN user_login_id VARCHAR;

COMMIT;