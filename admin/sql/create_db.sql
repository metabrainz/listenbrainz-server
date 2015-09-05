\set ON_ERROR_STOP 1

-- Create the user and the database. Must run as user postgres.

CREATE USER messybrainz NOCREATEDB NOCREATEUSER;
CREATE DATABASE messybrainz WITH OWNER = messybrainz TEMPLATE template0 ENCODING = 'UNICODE';
