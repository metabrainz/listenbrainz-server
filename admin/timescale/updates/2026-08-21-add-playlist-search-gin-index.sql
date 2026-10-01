-- GIN trigram index for playlist similarity search.
-- Without this, similarity() queries do sequential scans (~126s avg).
CREATE INDEX CONCURRENTLY playlist_name_trgm_gin ON playlist.playlist USING GIN (name gin_trgm_ops);
CREATE INDEX CONCURRENTLY playlist_description_trgm_gin ON playlist.playlist USING GIN (description gin_trgm_ops);
