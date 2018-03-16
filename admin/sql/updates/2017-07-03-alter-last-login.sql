BEGIN;

-- First update all null values with the created value for that row
UPDATE "user" SET last_login = created WHERE last_login IS NULL;

-- Alter the last_login column to add the NOT NULL constraint
ALTER TABLE "user" ALTER COLUMN last_login SET NOT NULL;

-- Alter the last_login column so that the default value becomes NOW()
ALTER TABLE "user" ALTER COLUMN last_login SET DEFAULT NOW();

COMMIT;
