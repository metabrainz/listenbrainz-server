-- Create the user and the database. Must run as user postgres.

CREATE USER timescale_lb_test NOCREATEDB NOSUPERUSER;
CREATE DATABASE timescale_lb_test WITH OWNER = timescale_lb_test TEMPLATE template0 ENCODING = 'UNICODE';
