-- This script resets the record listens flag for all
-- users, restarting their imports.

BEGIN;

UPDATE listens_importer
   SET error_message = NULL
 WHERE service = 'spotify';

COMMIT;
