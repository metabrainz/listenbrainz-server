BEGIN;

CREATE TABLE listen (
        listened_at     BIGINT                   NOT NULL,
        track_name      TEXT                     NOT NULL,
        user_name       TEXT                     NOT NULL,
        user_id         INTEGER                  NOT NULL,
        created         TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        data            JSONB                    NOT NULL
);

CREATE TABLE listen_delete_metadata (
    id                  SERIAL                      NOT NULL,
    user_id             INTEGER                     NOT NULL,
    listened_at         BIGINT                      NOT NULL,
    recording_msid      UUID                        NOT NULL
);

CREATE TABLE listen_user_metadata (
    user_id             INTEGER                     NOT NULL,
    count               BIGINT                      NOT NULL, -- count of listens the user has earlier than `created`
    min_listened_at     BIGINT, -- minimum listened_at timestamp seen for the user in listens till `created`
    max_listened_at     BIGINT, -- maximum listened_at timestamp seen for the user in listens till `created`
    created             TIMESTAMP WITH TIME ZONE    NOT NULL  -- the created timestamp when data for this user was updated last
);

-- 86400 seconds * 5 = 432000 seconds = 5 days
SELECT create_hypertable('listen', 'listened_at', chunk_time_interval => 432000);

-- Playlists

CREATE TABLE playlist.playlist (
    id serial,
    mbid uuid not null default uuid_generate_v4(),
    creator_id int not null, -- int, but not an fk because it's in the wrong database
    name text not null,
    description text,
    public boolean not null,
    created timestamp with time zone default now() not null,
    last_updated timestamp with time zone default now() not null,
    copied_from_id int, -- id of another playlist
    created_for_id int,
    additional_metadata jsonb
);

CREATE TABLE playlist.playlist_recording (
    id serial,
    playlist_id int not null,  --FK playlist.id
    position int not null,
    mbid uuid not null,
    added_by_id int not null,  -- int, but not an fk because it's in the wrong database
    created timestamp with time zone default now() not null,
    additional_metadata jsonb
);

CREATE TABLE playlist.playlist_collaborator (
    playlist_id int not null,  -- FK playlist.id
    collaborator_id int not null  -- link to user.id in main database
);

-- MBID Mapping

CREATE TABLE mbid_manual_mapping(
    id             INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    recording_msid UUID NOT NULL,
    recording_mbid UUID NOT NULL,
    user_id        INTEGER NOT NULL,
    created        TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE TABLE mbid_mapping (
        recording_msid      uuid not null,
        recording_mbid      uuid, -- FK mbid_mapping_metadata.recording_mbid
        match_type          mbid_mapping_match_type_enum NOT NULL,
        last_updated        TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        check_again         TIMESTAMP WITH TIME ZONE
);

CREATE TABLE mbid_mapping_metadata (
        artist_credit_id    INT NOT NULL,
        recording_mbid      UUID NOT NULL,
        release_mbid        UUID NOT NULL,
        release_name        TEXT NOT NULL,
        artist_mbids        UUID[] NOT NULL,
        artist_credit_name  TEXT NOT NULL,
        recording_name      TEXT NOT NULL,
        last_updated        TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- postgres does not enforce dimensionality of arrays. add explicit check to avoid regressions (once burnt, twice shy!).
ALTER TABLE mbid_mapping_metadata
    ADD CONSTRAINT mbid_mapping_metadata_artist_mbids_check
    CHECK ( array_ndims(artist_mbids) = 1 );

-- this table is defined in listenbrainz/mbid_mapping/mapping/mb_metadata_cache.py and created in production
-- there. this definition is only for tests and local development. remember to keep both in sync.
CREATE TABLE mapping.mb_metadata_cache (
    dirty               BOOLEAN DEFAULT FALSE,
    recording_mbid      UUID NOT NULL,
    artist_mbids        UUID[] NOT NULL,
    release_mbid        UUID,
    recording_data      JSONB NOT NULL,
    artist_data         JSONB NOT NULL,
    tag_data            JSONB NOT NULL,
    release_data        JSONB NOT NULL
);

-- postgres does not enforce dimensionality of arrays. add explicit check to avoid regressions (once burnt, twice shy!).
ALTER TABLE mapping.mb_metadata_cache
    ADD CONSTRAINT mb_metadata_cache_artist_mbids_check
    CHECK ( array_ndims(artist_mbids) = 1 );

-- the various mapping columns should only be null if the match_type is no_match, otherwise the columns should be
-- non null. we have had bugs where we completely forgot to insert values for a column and it went unchecked because
-- it is not possible to mark the column as NOT NULL. however, we can use this constraint to enforce the NOT NULL
-- check conditionally. this should help in preventing regressions and future bugs.
ALTER TABLE mbid_mapping
    ADD CONSTRAINT mbid_mapping_fields_null_check
    CHECK (
        (
              match_type = 'no_match'
          AND recording_mbid IS NULL
        ) OR (
              match_type <> 'no_match'
          AND recording_mbid IS NOT NULL
        )
    );


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



CREATE TABLE spotify_cache.raw_cache_data (
    id              INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    album_id        TEXT NOT NULL,
    data            JSONB,
    last_refresh    TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at      TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE spotify_cache.album (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    spotify_id              TEXT   NOT NULL,
    name                    TEXT   NOT NULL,
    type                    TEXT   NOT NULL,
    release_date            TEXT   NOT NULL,
    last_refresh            TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at              TIMESTAMP WITH TIME ZONE NOT NULL,
    data                    JSONB  NOT NULL
);

CREATE TABLE spotify_cache.artist (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    spotify_id              TEXT NOT NULL,
    name                    TEXT NOT NULL,
    data                    JSONB NOT NULL
);

CREATE TABLE spotify_cache.track (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    spotify_id              TEXT NOT NULL,
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

CREATE TABLE background_worker_state (
    key     TEXT NOT NULL,
    value   TEXT
);
COMMENT ON TABLE background_worker_state IS 'This table is used to store miscellaneous data by various background processes or the ListenBrainz webserver. Use it when storing the data is redis is not reliable enough.';


CREATE TABLE similarity.recording (
    mbid0 UUID NOT NULL,
    mbid1 UUID NOT NULL,
    metadata JSONB NOT NULL
);

CREATE TABLE similarity.artist_credit_mbids (
    mbid0 UUID NOT NULL,
    mbid1 UUID NOT NULL,
    metadata JSONB NOT NULL
);

COMMIT;
