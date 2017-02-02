-- Create the user and the database. Must run as user postgres.

CREATE USER listenbrainz NOCREATEDB NOCREATEUSER;
CREATE DATABASE listenbrainz WITH OWNER = listenbrainz TEMPLATE template0 ENCODING = 'UNICODE';
