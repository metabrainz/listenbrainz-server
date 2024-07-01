BEGIN;

CREATE SCHEMA soundcloud_cache;
CREATE TABLE soundcloud_cache.artist (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    artist_id               TEXT NOT NULL,
    name                    TEXT NOT NULL,
    data                    JSONB NOT NULL
);

CREATE TABLE soundcloud_cache.track (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    track_id                TEXT NOT NULL,
    name                    TEXT NOT NULL,
    artist_id               TEXT NOT NULL,
    data                    JSONB NOT NULL
);
CREATE UNIQUE INDEX soundcloud_cache_track_soundcloud_id_idx ON soundcloud_cache.track (track_id);
CREATE UNIQUE INDEX soundcloud_cache_artist_soundcloud_id_idx ON soundcloud_cache.artist (artist_id);

COMMIT;
