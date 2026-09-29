BEGIN;

CREATE TABLE listen (
    listened_at     TIMESTAMP WITH TIME ZONE NOT NULL,
    created         TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    user_id         INTEGER                  NOT NULL,
    recording_msid  UUID                     NOT NULL,
    data            JSONB                    NOT NULL
);

CREATE TABLE listen_user_metadata (
    user_id             INTEGER                     NOT NULL,
    count               BIGINT                      NOT NULL, -- count of listens the user has earlier than `created`
    min_listened_at     TIMESTAMP WITH TIME ZONE, -- minimum listened_at timestamp seen for the user in listens till `created`
    max_listened_at     TIMESTAMP WITH TIME ZONE, -- maximum listened_at timestamp seen for the user in listens till `created`
    created             TIMESTAMP WITH TIME ZONE    NOT NULL  -- the created timestamp when data for this user was updated last
);

SELECT create_hypertable('listen', 'listened_at', chunk_time_interval => INTERVAL '30 days');

CREATE TABLE messybrainz.submissions (
    id              INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    gid             UUID NOT NULL,
    recording       TEXT NOT NULL,
    artist_credit   TEXT NOT NULL,
    release         TEXT,
    track_number    TEXT,
    duration        INTEGER,
    submitted       TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE messybrainz.submissions_redirect (
    duplicate_msid UUID NOT NULL,
    original_msid UUID NOT NULL
);

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


CREATE TABLE similarity.recording_dev (
    mbid0 UUID NOT NULL,
    mbid1 UUID NOT NULL,
    metadata JSONB NOT NULL
);

CREATE TABLE similarity.recording (
    mbid0 UUID NOT NULL,
    mbid1 UUID NOT NULL,
    score INT NOT NULL
);

CREATE TABLE similarity.artist_credit_mbids_dev (
    mbid0 UUID NOT NULL,
    mbid1 UUID NOT NULL,
    metadata JSONB NOT NULL
);


CREATE TABLE similarity.artist_credit_mbids (
    mbid0 UUID NOT NULL,
    mbid1 UUID NOT NULL,
    score INT NOT NULL
);

CREATE TABLE similarity.overhyped_artists (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    artist_mbid             UUID NOT NULL,
    factor                  FLOAT
);

CREATE TABLE tags.lb_tag_radio (
    tag                     TEXT NOT NULL,
    recording_mbid          UUID NOT NULL,
    tag_count               INTEGER NOT NULL,
    percent                 DOUBLE PRECISION NOT NULL,
    source                  lb_tag_radio_source_type_enum NOT NULL
);

CREATE TABLE popularity.recording (
    recording_mbid          UUID NOT NULL,
    total_listen_count      INTEGER NOT NULL,
    total_user_count        INTEGER NOT NULL
);

CREATE TABLE popularity.mlhd_recording (
    recording_mbid          UUID NOT NULL,
    total_listen_count      INTEGER NOT NULL,
    total_user_count        INTEGER NOT NULL
);

CREATE TABLE popularity.artist (
    artist_mbid             UUID NOT NULL,
    total_listen_count      INTEGER NOT NULL,
    total_user_count        INTEGER NOT NULL
);

CREATE TABLE popularity.mlhd_artist (
    artist_mbid             UUID NOT NULL,
    total_listen_count      INTEGER NOT NULL,
    total_user_count        INTEGER NOT NULL
);

CREATE TABLE popularity.release (
    release_mbid            UUID NOT NULL,
    total_listen_count      INTEGER NOT NULL,
    total_user_count        INTEGER NOT NULL
);

CREATE TABLE popularity.mlhd_release (
    release_mbid            UUID NOT NULL,
    total_listen_count      INTEGER NOT NULL,
    total_user_count        INTEGER NOT NULL
);

CREATE TABLE popularity.release_group (
    release_group_mbid      UUID NOT NULL,
    total_listen_count      INTEGER NOT NULL,
    total_user_count        INTEGER NOT NULL
);

CREATE TABLE popularity.mlhd_release_group (
    release_group_mbid      UUID NOT NULL,
    total_listen_count      INTEGER NOT NULL,
    total_user_count        INTEGER NOT NULL
);

CREATE TABLE popularity.top_recording (
    artist_mbid             UUID NOT NULL,
    recording_mbid          UUID NOT NULL,
    total_listen_count      INTEGER NOT NULL,
    total_user_count        INTEGER NOT NULL
);

CREATE TABLE popularity.mlhd_top_recording (
    artist_mbid             UUID NOT NULL,
    recording_mbid          UUID NOT NULL,
    total_listen_count      INTEGER NOT NULL,
    total_user_count        INTEGER NOT NULL
);

CREATE TABLE popularity.top_release (
    artist_mbid             UUID NOT NULL,
    release_mbid            UUID NOT NULL,
    total_listen_count      INTEGER NOT NULL,
    total_user_count        INTEGER NOT NULL
);

CREATE TABLE popularity.mlhd_top_release (
    artist_mbid             UUID NOT NULL,
    release_mbid            UUID NOT NULL,
    total_listen_count      INTEGER NOT NULL,
    total_user_count        INTEGER NOT NULL
);


CREATE TABLE popularity.top_release_group (
    artist_mbid             UUID NOT NULL,
    release_group_mbid      UUID NOT NULL,
    total_listen_count      INTEGER NOT NULL,
    total_user_count        INTEGER NOT NULL
);

CREATE TABLE popularity.mlhd_top_release_group (
    artist_mbid             UUID NOT NULL,
    release_group_mbid      UUID NOT NULL,
    total_listen_count      INTEGER NOT NULL,
    total_user_count        INTEGER NOT NULL
);

CREATE TABLE statistics.year_in_music_cover (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    user_id             INTEGER NOT NULL,
    year                SMALLINT NOT NULL,
    caa_id              BIGINT,
    caa_release_mbid    UUID
);

COMMIT;
