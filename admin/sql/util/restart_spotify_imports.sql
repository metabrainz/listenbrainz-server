-- This script resets the record listens flag for all
-- users, restarting their imports.

BEGIN;

UPDATE spotify_auth
   SET record_listens = 't',
       error_message = NULL;

COMMIT;
