-- For empty installations only. For existing data, copy the spotify_cache, apple_cache, soundcloud_cache
-- and internetarchive_cache schemas from Timescale with pg_dump/pg_restore instead.
BEGIN;
CREATE SCHEMA spotify_cache;
CREATE SCHEMA apple_cache;
CREATE SCHEMA soundcloud_cache;
CREATE SCHEMA internetarchive_cache;

CREATE TABLE spotify_cache.album (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    album_id                TEXT   NOT NULL,
    name                    TEXT   NOT NULL,
    type                    TEXT   NOT NULL,
    release_date            TEXT   NOT NULL,
    last_refresh            TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at              TIMESTAMP WITH TIME ZONE NOT NULL,
    data                    JSONB  NOT NULL
);

CREATE TABLE spotify_cache.artist (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    artist_id               TEXT NOT NULL,
    name                    TEXT NOT NULL,
    data                    JSONB NOT NULL
);

CREATE TABLE spotify_cache.track (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    track_id                TEXT NOT NULL,
    name                    TEXT NOT NULL,
    track_number            INTEGER NOT NULL,
    album_id                TEXT NOT NULL,
    data                    JSONB NOT NULL
);

CREATE TABLE spotify_cache.rel_album_artist (
    id              INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    album_id        TEXT NOT NULL,
    artist_id       TEXT NOT NULL,
    position        INTEGER NOT NULL
);

CREATE TABLE spotify_cache.rel_track_artist (
    id              INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    track_id        TEXT NOT NULL,
    artist_id       TEXT NOT NULL,
    position        INTEGER NOT NULL
);

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
    release_year            INTEGER,
    release_month           INTEGER,
    release_day             INTEGER,
    data                    JSONB NOT NULL
);


CREATE TABLE internetarchive_cache.track (
    id            INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    track_id      TEXT UNIQUE NOT NULL,
    name          TEXT NOT NULL,
    artist        TEXT[] NOT NULL,
    album         TEXT,
    stream_urls   TEXT[] NOT NULL,
    artwork_url   TEXT,
    data          JSONB NOT NULL,
    last_updated  TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX spotify_cache_album_spotify_id_idx ON spotify_cache.album (album_id);
CREATE UNIQUE INDEX spotify_cache_artist_spotify_id_idx ON spotify_cache.artist (artist_id);
CREATE UNIQUE INDEX spotify_cache_track_spotify_id_idx ON spotify_cache.track (track_id);
CREATE INDEX spotify_cache_rel_album_artist_track_id_idx ON spotify_cache.rel_album_artist (album_id);
CREATE INDEX spotify_cache_rel_track_artist_track_id_idx ON spotify_cache.rel_track_artist (track_id);

CREATE UNIQUE INDEX apple_cache_album_apple_id_idx ON apple_cache.album (album_id);
CREATE UNIQUE INDEX apple_cache_artist_apple_id_idx ON apple_cache.artist (artist_id);
CREATE UNIQUE INDEX apple_cache_track_apple_id_idx ON apple_cache.track (track_id);
CREATE INDEX apple_cache_rel_album_artist_track_id_idx ON apple_cache.rel_album_artist (album_id);
CREATE INDEX apple_cache_rel_track_artist_track_id_idx ON apple_cache.rel_track_artist (track_id);

CREATE UNIQUE INDEX soundcloud_cache_track_soundcloud_id_idx ON soundcloud_cache.track (track_id);
CREATE UNIQUE INDEX soundcloud_cache_artist_soundcloud_id_idx ON soundcloud_cache.artist (artist_id);

-- Internet Archive indexes
CREATE UNIQUE INDEX internetarchive_cache_track_track_id_idx ON internetarchive_cache.track (track_id);
CREATE INDEX internetarchive_cache_track_artist_gin_idx ON internetarchive_cache.track USING GIN (artist);
CREATE INDEX internetarchive_cache_track_name_idx ON internetarchive_cache.track (name);
CREATE INDEX internetarchive_cache_track_album_idx ON internetarchive_cache.track (album);
CREATE INDEX internetarchive_cache_track_stream_urls_gin_idx ON internetarchive_cache.track USING GIN (stream_urls);
CREATE INDEX internetarchive_cache_track_last_updated_idx ON internetarchive_cache.track (last_updated);
COMMIT;
