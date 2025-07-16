BEGIN;

CREATE SCHEMA IF NOT EXISTS internetarchive_cache;

-- Create the new table with updated structure
CREATE TABLE internetarchive_cache.track (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    track_id      TEXT UNIQUE NOT NULL,
    name          TEXT NOT NULL,
    artist        TEXT[] NOT NULL,
    album         TEXT,
    stream_urls   TEXT[] NOT NULL,
    artwork_url   TEXT,
    data          JSONB NOT NULL,
    last_updated  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for the new table structure
CREATE UNIQUE INDEX internetarchive_cache_track_track_id_idx ON internetarchive_cache.track (track_id);
CREATE INDEX internetarchive_cache_track_artist_gin_idx ON internetarchive_cache.track USING GIN (artist);
CREATE INDEX internetarchive_cache_track_name_idx ON internetarchive_cache.track (name);
CREATE INDEX internetarchive_cache_track_album_idx ON internetarchive_cache.track (album);
CREATE INDEX internetarchive_cache_track_stream_urls_gin_idx ON internetarchive_cache.track USING GIN (stream_urls);
CREATE INDEX internetarchive_cache_track_last_updated_idx ON internetarchive_cache.track (last_updated);

COMMIT;
