-- Create the user and the database. Must run as user postgres.

CREATE USER messybrainz NOCREATEDB NOSUPERUSER;
CREATE DATABASE messybrainz WITH OWNER = messybrainz TEMPLATE template0 ENCODING = 'UNICODE';
