\set ON_ERROR_STOP 1

-- Create the user and the database. Must run as user postgres.

CREATE USER ab_test NOCREATEDB NOCREATEUSER;
CREATE DATABASE ab_test WITH OWNER = ab_test TEMPLATE template0 ENCODING = 'UNICODE';
