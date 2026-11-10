BEGIN;

DELETE FROM listen                      CASCADE;
DELETE FROM listen_user_metadata        CASCADE;

COMMIT;
