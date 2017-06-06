BEGIN;

DROP TABLE IF EXISTS "user"               CASCADE;
DROP TABLE IF EXISTS listen               CASCADE;
DROP TABLE IF EXISTS listen_json          CASCADE;

DROP TABLE IF EXISTS api_compat.token     CASCADE;
DROP TABLE IF EXISTS api_compat.session   CASCADE;

DROP TABLE IF EXISTS statistics.user      CASCADE;
DROP TABLE IF EXISTS statistics.artist    CASCADE;
DROP TABLE IF EXISTS statistics.release   CASCADE;
DROP TABLE IF EXISTS statistics.recording CASCADE;

COMMIT;
