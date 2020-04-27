-- Create the user and the database. Must run as user postgres.

CREATE USER listenbrainz_ts_test NOCREATEDB NOSUPERUSER;
CREATE DATABASE listenbrainz_ts_test WITH OWNER = listenbrainz_ts_test TEMPLATE template0 ENCODING = 'UNICODE';
