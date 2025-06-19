BEGIN;

CREATE SCHEMA IF NOT EXISTS internetarchive_cache;

CREATE TABLE internetarchive_cache.track (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    track_id      TEXT UNIQUE NOT NULL,
    title         TEXT NOT NULL,
    creator       TEXT,
    artist        TEXT,
    album         TEXT,
    year          TEXT,
    notes         TEXT,
    topics        TEXT,
    stream_url    TEXT NOT NULL,
    duration      INTEGER,
    artwork_url   TEXT,
    date          TEXT,
    data          JSONB NOT NULL,
    last_updated  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE UNIQUE INDEX internetarchive_cache_track_track_id_idx ON internetarchive_cache.track (track_id);
CREATE INDEX internetarchive_cache_track_creator_idx ON internetarchive_cache.track (creator);
CREATE INDEX internetarchive_cache_track_artist_idx ON internetarchive_cache.track (artist);
CREATE INDEX internetarchive_cache_track_title_idx ON internetarchive_cache.track (title);
CREATE INDEX internetarchive_cache_track_album_idx ON internetarchive_cache.track (album);
CREATE INDEX internetarchive_cache_track_year_idx ON internetarchive_cache.track (year);
CREATE INDEX internetarchive_cache_track_notes_idx ON internetarchive_cache.track (notes);
CREATE INDEX internetarchive_cache_track_topics_idx ON internetarchive_cache.track (topics);

COMMIT;
