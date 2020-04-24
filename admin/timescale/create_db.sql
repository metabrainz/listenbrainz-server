-- Create the user and the database. Must run as user postgres.

CREATE USER listenbrainz_ts NOCREATEDB NOSUPERUSER;
ALTER USER listenbrainz_ts WITH PASSWORD 'listenbrainz_ts';
CREATE DATABASE listenbrainz_ts WITH OWNER = listenbrainz_ts TEMPLATE template1 ENCODING = 'UNICODE';
