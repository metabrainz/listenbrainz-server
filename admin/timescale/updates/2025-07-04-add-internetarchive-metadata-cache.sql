
BEGIN;

CREATE SCHEMA internetarchive_cache;
CREATE TABLE internetarchive_cache.track (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    track_id                TEXT NOT NULL,
    title                   TEXT NOT NULL,
    artist                  TEXT,
    data                    JSONB NOT NULL
);

CREATE UNIQUE INDEX internetarchive_cache_track_id_idx ON internetarchive_cache.track (track_id);
CREATE INDEX internetarchive_cache_track_artist_idx ON internetarchive_cache.track (artist);
CREATE INDEX internetarchive_cache_track_title_idx ON internetarchive_cache.track (title);

COMMIT;