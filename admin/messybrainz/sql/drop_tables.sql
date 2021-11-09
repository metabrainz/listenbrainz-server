BEGIN;

DROP TABLE IF EXISTS artist_credit                CASCADE;
DROP TABLE IF EXISTS recording                    CASCADE;
DROP TABLE IF EXISTS recording_json               CASCADE;
DROP TABLE IF EXISTS release                      CASCADE;

COMMIT;
