CREATE EXTENSION IF NOT EXISTS "pg_trgm";
ALTER DATABASE listenbrainz SET pg_trgm.word_similarity_threshold = 0.1;
BEGIN;
CREATE INDEX CONCURRENTLY user_name_search_trgm_idx ON "user" USING GIST (musicbrainz_id gist_trgm_ops);
COMMIT;
