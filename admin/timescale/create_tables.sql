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

COMMIT;
