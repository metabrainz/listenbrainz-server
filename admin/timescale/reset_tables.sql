BEGIN;

DELETE FROM listen                      CASCADE;
DELETE FROM listen_delete_metadata      CASCADE;
DELETE FROM listen_user_metadata        CASCADE;
DELETE FROM mbid_mapping                CASCADE;
DELETE FROM mapping.mb_metadata_cache   CASCADE;
DELETE FROM messybrainz.submissions     CASCADE;
DELETE FROM mbid_manual_mapping         CASCADE;
DELETE FROM playlist.playlist           CASCADE;

COMMIT;
