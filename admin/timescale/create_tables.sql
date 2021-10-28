BEGIN;

CREATE TABLE listen (
        listened_at     BIGINT                   NOT NULL,
        track_name      TEXT                     NOT NULL,
        user_name       TEXT                     NOT NULL,
        created         TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        data            JSONB                    NOT NULL
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

create table listen_join_listen_mbid_mapping (
        recording_msid      uuid not null,
        listen_mbid_mapping int not null -- FK listen_mbid_mapping.id
);

create table listen_mbid_mapping (
        id                  SERIAL,
        artist_credit_id    INT,
        recording_mbid      UUID,
        release_mbid        UUID,
        release_name        TEXT,
        artist_mbids        UUID[],
        artist_credit_name  TEXT,
        recording_name      TEXT,
        match_type          mbid_mapping_match_type_enum NOT NULL,
        last_updated        TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- postgres does not enforce dimensionality of arrays. add explicit check to avoid regressions (once burnt, twice shy!).
ALTER TABLE listen_mbid_mapping
    ADD CONSTRAINT listen_mbid_mapping_artist_mbids_check
    CHECK ( array_ndims(artist_mbids) = 1 );

-- the various mapping columns should only be null if the match_type is no_match, otherwise the columns should be
-- non null. we have had bugs where we completely forgot to insert values for a column and it went unchecked because
-- it is not possible to mark the column as NOT NULL. however, we can use this constraint to enforce the NOT NULL
-- check conditionally. this should help in preventing regressions and future bugs.
ALTER TABLE listen_mbid_mapping
    ADD CONSTRAINT listen_mbid_mapping_fields_null_check
    CHECK (
        (
              match_type = 'no_match'
          AND artist_credit_id IS NULL
          AND recording_mbid IS NULL
          AND release_mbid IS NULL
          AND release_name IS NULL
          AND artist_mbids IS NULL
          AND artist_credit_name IS NULL
          AND recording_name IS NULL
        ) OR (
              match_type <> 'no_match'
          AND artist_credit_id IS NOT NULL
          AND recording_mbid IS NOT NULL
          AND release_mbid IS NOT NULL
          AND release_name IS NOT NULL
          AND artist_mbids IS NOT NULL
          AND artist_credit_name IS NOT NULL
          AND recording_name IS NOT NULL
        )
    );

COMMIT;
