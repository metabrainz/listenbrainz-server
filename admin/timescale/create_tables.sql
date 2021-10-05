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

COMMIT;
