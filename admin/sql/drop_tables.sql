BEGIN;

DROP TABLE IF EXISTS "user"                         CASCADE;
DROP TABLE IF EXISTS data_dump                      CASCADE;
DROP TABLE IF EXISTS spotify_auth                   CASCADE;
DROP TABLE IF EXISTS external_service_oauth         CASCADE;
DROP TABLE IF EXISTS recording_feedback             CASCADE;
DROP TABLE IF EXISTS missing_musicbrainz_data       CASCADE;
DROP TABLE IF EXISTS user_relationship              CASCADE;
DROP TABLE IF EXISTS recommendation_feedback        CASCADE;
DROP TABLE IF EXISTS user_timeline_event            CASCADE;

COMMIT;
