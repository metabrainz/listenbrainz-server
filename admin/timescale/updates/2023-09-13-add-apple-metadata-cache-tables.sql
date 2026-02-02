BEGIN;

CREATE SCHEMA apple_cache;

CREATE TABLE apple_cache.album (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    album_id                TEXT   NOT NULL,
    name                    TEXT   NOT NULL,
    type                    TEXT   NOT NULL,
    release_date            TEXT   NOT NULL,
    last_refresh            TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at              TIMESTAMP WITH TIME ZONE NOT NULL,
    data                    JSONB  NOT NULL
);

CREATE TABLE apple_cache.artist (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    artist_id               TEXT NOT NULL,
    name                    TEXT NOT NULL,
    data                    JSONB NOT NULL
);

CREATE TABLE apple_cache.track (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    track_id                TEXT NOT NULL,
    name                    TEXT NOT NULL,
    track_number            INTEGER NOT NULL,
    album_id                TEXT NOT NULL,
    data                    JSONB NOT NULL
);

CREATE TABLE apple_cache.rel_album_artist (
    id              INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    album_id        TEXT NOT NULL,
    artist_id       TEXT NOT NULL,
    position        INTEGER NOT NULL
);

CREATE TABLE apple_cache.rel_track_artist (
    id              INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    track_id        TEXT NOT NULL,
    artist_id       TEXT NOT NULL,
    position        INTEGER NOT NULL
);

CREATE UNIQUE INDEX apple_cache_album_apple_id_idx ON apple_cache.album (album_id);
CREATE UNIQUE INDEX apple_cache_artist_apple_id_idx ON apple_cache.artist (artist_id);
CREATE UNIQUE INDEX apple_cache_track_apple_id_idx ON apple_cache.track (track_id);
CREATE INDEX apple_cache_rel_album_artist_track_id_idx ON apple_cache.rel_album_artist (album_id);
CREATE INDEX apple_cache_rel_track_artist_track_id_idx ON apple_cache.rel_track_artist (track_id);

COMMIT;
