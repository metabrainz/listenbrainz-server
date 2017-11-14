-- Create the user and the database. Must run as user postgres.

CREATE USER lb_test NOCREATEDB NOSUPERUSER;
CREATE DATABASE lb_test WITH OWNER = lb_test TEMPLATE template0 ENCODING = 'UNICODE';
