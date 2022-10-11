BEGIN;

CREATE SCHEMA spotify_cache;


CREATE UNLOGGED TABLE spotify_cache.raw_cache_data (
    id              INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    album_id        TEXT NOT NULL,
    data            JSONB,
    last_refresh    TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at      TIMESTAMP WITH TIME ZONE NOT NULL
);


CREATE UNLOGGED TABLE spotify_cache.album (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    spotify_id              TEXT   NOT NULL,
    name                    TEXT   NOT NULL,
    type                    TEXT   NOT NULL,
    release_date            TEXT   NOT NULL,
    last_refresh            TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at              TIMESTAMP WITH TIME ZONE NOT NULL,
    data                    JSONB  NOT NULL
);

CREATE UNLOGGED TABLE spotify_cache.artist (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    spotify_id              TEXT NOT NULL,
    name                    TEXT NOT NULL,
    data                    JSONB NOT NULL
);

CREATE UNLOGGED TABLE spotify_cache.track (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    spotify_id              TEXT NOT NULL,
    name                    TEXT NOT NULL,
    track_number            INTEGER NOT NULL,
    album_id                TEXT NOT NULL,
    data                    JSONB NOT NULL
);

CREATE UNLOGGED TABLE spotify_cache.rel_album_artist (
    id              INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    album_id        TEXT NOT NULL,
    artist_id       TEXT NOT NULL,
    position        INTEGER NOT NULL
);

CREATE UNLOGGED TABLE spotify_cache.rel_track_artist (
    id              INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    track_id        TEXT NOT NULL,
    artist_id       TEXT NOT NULL,
    position        INTEGER NOT NULL
);

COMMIT;
