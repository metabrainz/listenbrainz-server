BEGIN;

CREATE TABLE listen (
        listened_at     BIGINT                   NOT NULL,
        track_name      TEXT                     NOT NULL,
        user_name       TEXT                     NOT NULL,
        user_id         INTEGER                  NOT NULL,
        created         TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        data            JSONB                    NOT NULL
);

CREATE TABLE listen_helper (
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
    algorithm_metadata jsonb
);

CREATE TABLE playlist.playlist_recording (
    id serial,
    playlist_id int not null,  --FK playlist.id
    position int not null,
    mbid uuid not null,
    added_by_id int not null,  -- int, but not an fk because it's in the wrong database
    created timestamp with time zone default now() not null
);

CREATE TABLE  playlist.playlist_collaborator (
    playlist_id int not null,  -- FK playlist.id
    collaborator_id int not null  -- link to user.id in main database
);

-- MBID Mapping

CREATE TABLE mbid_mapping (
        recording_msid      uuid not null,
        recording_mbid      uuid, -- FK mbid_mapping_metadata.recording_mbid
        match_type          mbid_mapping_match_type_enum NOT NULL,
        last_updated        TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
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

COMMIT;
