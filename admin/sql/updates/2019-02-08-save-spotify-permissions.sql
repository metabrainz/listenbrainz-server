BEGIN;

-- rename active to record_listens
ALTER TABLE spotify_auth RENAME active TO record_listens;

-- add column permission to table
ALTER TABLE spotify_auth ADD COLUMN permission VARCHAR;
-- set value to 'user-read-recently-played' for all current users
UPDATE spotify_auth
   SET permission = 'user-read-recently-played';
-- set the column as not null
ALTER TABLE spotify_auth ALTER COLUMN permission SET NOT NULL;

COMMIT;
