CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
ALTER DATABASE listenbrainz SET pg_trgm.word_similarity_threshold = 0.1;
CREATE EXTENSION IF NOT EXISTS "cube";
