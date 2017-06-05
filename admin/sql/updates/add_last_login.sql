BEGIN;

-- Add column for last login to user table
ALTER TABLE "user" ADD COLUMN last_login TIMESTAMP WITH TIME ZONE;

COMMIT;
