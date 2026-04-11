BEGIN;

DELETE FROM listen                      CASCADE;
DELETE FROM listen_user_metadata        CASCADE;

DELETE FROM youtube_cache.video;

COMMIT;
