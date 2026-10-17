-- Listens are hash-partitioned by user_id. The table, partitions and indexes are created
-- by `manage.py init_listens_db` (see also create_indexes.sql).
BEGIN;

CREATE TABLE listen (
    listened_at     TIMESTAMP WITH TIME ZONE NOT NULL,
    created         TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    user_id         INTEGER                  NOT NULL,
    recording_msid  UUID                     NOT NULL,
    data            JSONB                    NOT NULL
) PARTITION BY HASH (user_id);

CREATE TABLE listen_delete_metadata (
    id                  SERIAL                      NOT NULL,
    user_id             INTEGER                     NOT NULL,
    listened_at         TIMESTAMP WITH TIME ZONE    NOT NULL,
    recording_msid      UUID                        NOT NULL,
    status              listen_delete_metadata_status_enum NOT NULL DEFAULT 'pending',
    listen_created      TIMESTAMP WITH TIME ZONE
);

CREATE TABLE listen_user_metadata (
    user_id             INTEGER                     NOT NULL,
    count               BIGINT                      NOT NULL,
    min_listened_at     TIMESTAMP WITH TIME ZONE,
    max_listened_at     TIMESTAMP WITH TIME ZONE
);

CREATE TABLE deleted_user_listen_history (
    id                          INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    user_id                     INTEGER NOT NULL,
    max_created                 TIMESTAMP WITH TIME ZONE NOT NULL
);

-- MBID mapping, MusicBrainz metadata caches and lookup indexes

CREATE TABLE mapping.mbid_manual_mapping (
    id             INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    recording_msid UUID NOT NULL,
    recording_mbid UUID NOT NULL,
    user_id        INTEGER NOT NULL,
    created        TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE TABLE mapping.mbid_mapping (
        recording_msid      uuid not null,
        recording_mbid      uuid, -- FK mapping.mbid_mapping_metadata.recording_mbid
        match_type          mapping.mbid_mapping_match_type_enum NOT NULL,
        last_updated        TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        check_again         TIMESTAMP WITH TIME ZONE
);

CREATE TABLE mapping.mbid_mapping_metadata (
        artist_credit_id    INT NOT NULL,
        recording_mbid      UUID NOT NULL,
        release_mbid        UUID NOT NULL,
        release_name        TEXT NOT NULL,
        artist_mbids        UUID[] NOT NULL,
        artist_credit_name  TEXT NOT NULL,
        recording_name      TEXT NOT NULL,
        last_updated        TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE TABLE mapping.mb_metadata_cache (
    dirty               BOOLEAN DEFAULT FALSE,
    last_updated        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    recording_mbid      UUID NOT NULL,
    recording_id        INTEGER NOT NULL,
    artist_mbids        UUID[] NOT NULL,
    artist_ids          INTEGER[] NOT NULL,
    release_mbid        UUID,
    release_id          INTEGER,
    release_group_id    INTEGER,
    recording_data      JSONB NOT NULL,
    artist_data         JSONB NOT NULL,
    tag_data            JSONB NOT NULL,
    release_data        JSONB NOT NULL
);

CREATE TABLE mapping.mb_release_group_cache (
    dirty                   BOOLEAN DEFAULT FALSE,
    last_updated            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    release_group_mbid      UUID NOT NULL,
    artist_mbids            UUID[] NOT NULL,
    artist_data             JSONB NOT NULL,
    tag_data                JSONB NOT NULL,
    release_group_data      JSONB NOT NULL,
    recording_data          JSONB NOT NULL
);

CREATE TABLE mapping.mb_artist_metadata_cache (
    dirty                   BOOLEAN DEFAULT FALSE,
    last_updated            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    artist_mbid             UUID NOT NULL,
    artist_data             JSONB NOT NULL,
    tag_data                JSONB NOT NULL,
    release_group_data      JSONB NOT NULL
);

CREATE TABLE mapping.canonical_musicbrainz_data (
    id                  SERIAL,
    artist_credit_id    INT NOT NULL,
    artist_mbids        UUID[] NOT NULL,
    artist_credit_name  TEXT NOT NULL,
    release_mbid        UUID NOT NULL,
    release_name        TEXT NOT NULL,
    recording_mbid      UUID NOT NULL,
    recording_name      TEXT NOT NULL,
    combined_lookup     TEXT NOT NULL,
    score               INTEGER NOT NULL
);

CREATE TABLE mapping.canonical_musicbrainz_data_release_support (
    id                  SERIAL,
    artist_credit_id    INT NOT NULL,
    artist_mbids        UUID[] NOT NULL,
    artist_credit_name  TEXT NOT NULL,
    release_mbid        UUID NOT NULL,
    release_name        TEXT NOT NULL,
    recording_mbid      UUID NOT NULL,
    recording_name      TEXT NOT NULL,
    combined_lookup     TEXT NOT NULL,
    score               INTEGER NOT NULL
);

CREATE TABLE mapping.canonical_recording_redirect (
    id                          SERIAL,
    recording_mbid              UUID NOT NULL,
    canonical_recording_mbid    UUID NOT NULL,
    canonical_release_mbid      UUID NOT NULL
);

CREATE TABLE mapping.canonical_release_redirect (
    id                          SERIAL,
    release_mbid                UUID NOT NULL,
    canonical_release_mbid      UUID NOT NULL,
    release_group_mbid          UUID NOT NULL
);

CREATE TABLE mapping.spotify_metadata_index (
    id                              SERIAL,
    artist_ids                      TEXT NOT NULL,
    album_id                        TEXT NOT NULL,
    track_id                        TEXT NOT NULL,
    combined_lookup_all             TEXT NOT NULL,
    combined_lookup_without_album   TEXT NOT NULL,
    score                           INTEGER NOT NULL
);

CREATE TABLE mapping.apple_metadata_index (
    id                              SERIAL,
    artist_ids                      TEXT NOT NULL,
    album_id                        TEXT NOT NULL,
    track_id                        TEXT NOT NULL,
    combined_lookup_all             TEXT NOT NULL,
    combined_lookup_without_album   TEXT NOT NULL,
    score                           INTEGER NOT NULL
);

CREATE TABLE mapping.soundcloud_metadata_index (
    id                              SERIAL,
    artist_id                       TEXT NOT NULL,
    track_id                        TEXT NOT NULL,
    combined_lookup_without_album   TEXT NOT NULL,
    score                           INTEGER NOT NULL
);

CREATE TABLE mapping.background_worker_state (
    key     TEXT NOT NULL,
    value   TEXT
);

-- postgres does not enforce dimensionality of arrays. add explicit check to avoid regressions (once burnt, twice shy!).
ALTER TABLE mapping.mbid_mapping_metadata
    ADD CONSTRAINT mbid_mapping_metadata_artist_mbids_check
    CHECK ( array_ndims(artist_mbids) = 1 );

-- this table is defined in mbid_mapping/mapping/mb_metadata_cache.py and created in production
-- there. this definition is only for tests and local development. remember to keep both in sync.
ALTER TABLE mapping.mb_metadata_cache
        ADD CONSTRAINT mb_metadata_cache_artist_mbids_check
        CHECK ( array_ndims(artist_mbids) = 1 );

ALTER TABLE mapping.mb_metadata_cache
        ADD CONSTRAINT mb_metadata_cache_artist_ids_check
        CHECK ( array_ndims(artist_ids) = 1 );

ALTER TABLE mapping.mb_release_group_cache
        ADD CONSTRAINT mb_release_group_cache_artist_mbids_check
        CHECK ( array_ndims(artist_mbids) = 1 );

-- The following mapping tables are defined in mbid_mapping/mapping and created in production
-- there. These definitions are only for tests and local development. Remember to keep both in sync.
-- the various mapping columns should only be null if the match_type is no_match, otherwise the columns should be
-- non null. we have had bugs where we completely forgot to insert values for a column and it went unchecked because
-- it is not possible to mark the column as NOT NULL. however, we can use this constraint to enforce the NOT NULL
-- check conditionally. this should help in preventing regressions and future bugs.
ALTER TABLE mapping.mbid_mapping
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

COMMENT ON TABLE mapping.background_worker_state IS 'This table is used by the mbid mapping cron jobs to store the last update timestamps of the metadata caches.';

ALTER TABLE listen_delete_metadata
    ADD CONSTRAINT listen_delete_metadata_status_created_constraint
    CHECK ( status = 'invalid' OR status = 'pending' OR (status = 'complete' AND listen_created IS NOT NULL) );

COMMIT;
