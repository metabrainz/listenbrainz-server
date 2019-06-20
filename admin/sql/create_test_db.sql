-- Create the user and the database. Must run as user postgres.

CREATE USER msb_test NOCREATEDB NOSUPERUSER;
CREATE DATABASE msb_test WITH OWNER = msb_test TEMPLATE template0 ENCODING = 'UNICODE'
