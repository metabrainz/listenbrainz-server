-- Create the user and the database. Must run as user postgres.

CREATE USER timescale_lb NOCREATEDB NOSUPERUSER;
ALTER USER timescale_lb WITH PASSWORD 'timescale_lb';
CREATE DATABASE timescale_lb WITH OWNER = timescale_lb TEMPLATE template1 ENCODING = 'UNICODE';
