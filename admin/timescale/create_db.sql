-- Create the user and the database. Must run as user postgres.

CREATE USER timescale_lb NOCREATEDB NOSUPERUSER;
CREATE DATABASE timescale_lb WITH OWNER = timescale_lb TEMPLATE template0 ENCODING = 'UNICODE';
