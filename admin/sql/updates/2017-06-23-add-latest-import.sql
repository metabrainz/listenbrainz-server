BEGIN;

-- Add latest_import timestamp column to "user" table
ALTER TABLE "user" ADD COLUMN latest_import TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT TIMESTAMP 'epoch';

COMMIT;
