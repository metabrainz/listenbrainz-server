CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
-- The following line is now executed by the init-db action from manage.py. If you create a DB without the init-db function
-- you will need to execute the following ALTER in order to complete your DB setup.
--ALTER DATABASE listenbrainz SET pg_trgm.word_similarity_threshold = 0.1;
CREATE EXTENSION IF NOT EXISTS "cube";
