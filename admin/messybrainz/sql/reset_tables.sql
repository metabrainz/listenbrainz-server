BEGIN;

DELETE FROM artist_credit                CASCADE;
DELETE FROM recording                    CASCADE;
DELETE FROM recording_json               CASCADE;
DELETE FROM release                      CASCADE;

COMMIT;
