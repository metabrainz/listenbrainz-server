CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
ALTER DATABASE listenbrainz SET pg_trgm.similarity_threshold = 0.1;
