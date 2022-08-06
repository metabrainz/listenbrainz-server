BEGIN;

TRUNCATE "user"                         CASCADE;
TRUNCATE data_dump                      CASCADE;
TRUNCATE spotify_auth                   CASCADE;
TRUNCATE external_service_oauth         CASCADE;
TRUNCATE listens_importer               CASCADE;
TRUNCATE recording_feedback             CASCADE;
TRUNCATE missing_musicbrainz_data       CASCADE;
TRUNCATE user_relationship              CASCADE;
TRUNCATE recommendation_feedback        CASCADE;
TRUNCATE user_timeline_event            CASCADE;
TRUNCATE hide_user_timeline_event       CASCADE;
TRUNCATE reported_users                 CASCADE;
TRUNCATE pinned_recording               CASCADE;
TRUNCATE release_color                  CASCADE;
TRUNCATE user_setting                   CASCADE;

COMMIT;
