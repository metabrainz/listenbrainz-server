CREATE EXTENSION IF NOT EXISTS "pg_trgm";
ALTER DATABASE listenbrainz_ts SET pg_trgm.word_similarity_threshold = 0.1;
