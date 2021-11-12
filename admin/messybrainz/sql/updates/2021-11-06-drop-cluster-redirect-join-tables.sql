BEGIN;

DROP TABLE IF EXISTS artist_credit_cluster;
DROP TABLE IF EXISTS artist_credit_redirect;
DROP TABLE IF EXISTS recording_artist_join;
DROP TABLE IF EXISTS recording_cluster;
DROP TABLE IF EXISTS recording_redirect;
DROP TABLE IF EXISTS recording_release_join;
DROP TABLE IF EXISTS release_cluster;
DROP TABLE IF EXISTS release_redirect;

COMMIT;