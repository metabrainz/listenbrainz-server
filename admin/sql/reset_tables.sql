BEGIN;

-- this file lists all tables from create_tables.sql in order so that we don't miss resetting any. currently unused tables are commented out.
DELETE FROM "user"                         CASCADE;
DELETE FROM reported_users                 CASCADE;

DELETE FROM api_compat.session             CASCADE;
DELETE FROM api_compat.token               CASCADE;

DELETE FROM data_dump                      CASCADE;
DELETE FROM missing_musicbrainz_data       CASCADE;

DELETE FROM recommendation.cf_recording    CASCADE;
-- DELETE FROM recommendation.recommender     CASCADE;
-- DELETE FROM recommendation.recommender_session    CASCADE;
-- DELETE FROM recommendation.recording_session    CASCADE;
DELETE FROM recommendation.similar_user    CASCADE;

DELETE FROM user_timeline_event            CASCADE;
DELETE FROM hide_user_timeline_event       CASCADE;

-- DELETE FROM spotify_auth                   CASCADE;
DELETE FROM external_service_oauth         CASCADE;
DELETE FROM listens_importer               CASCADE;

DELETE FROM recording_feedback             CASCADE;
DELETE FROM recommendation_feedback        CASCADE;
DELETE FROM user_relationship              CASCADE;
DELETE FROM release_color                  CASCADE;
DELETE FROM pinned_recording               CASCADE;
DELETE FROM user_setting                   CASCADE;

COMMIT;
