BEGIN;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE SCHEMA playlist;


CREATE TABLE playlist.playlist (
    id serial,
    mbid uuid not null default gen_random_uuid(),
    creator_id int not null, -- user.id; validated by the application
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
    added_by_id int not null,  -- user.id; validated by the application
    created timestamp with time zone default now() not null,
    additional_metadata jsonb
);

CREATE TABLE playlist.playlist_collaborator (
    playlist_id int not null,  -- FK playlist.id
    collaborator_id int not null  -- link to user.id in main database
);

ALTER TABLE playlist.playlist ADD CONSTRAINT playlist_pkey PRIMARY KEY (id);

ALTER TABLE playlist.playlist_recording ADD CONSTRAINT playlist_recording_pkey PRIMARY KEY (id);

CREATE UNIQUE INDEX mbid_playlist ON playlist.playlist (mbid);

CREATE INDEX creator_id_playlist ON playlist.playlist (creator_id);

CREATE INDEX copied_from_id_playlist ON playlist.playlist (copied_from_id);

CREATE INDEX created_for_id_playlist ON playlist.playlist (created_for_id);

CREATE INDEX playlist_id_playlist_recording ON playlist.playlist_recording (playlist_id);

CREATE INDEX mbid_playlist_recording ON playlist.playlist_recording (mbid);

CREATE INDEX added_by_id_playlist_recording ON playlist.playlist_recording (added_by_id);

CREATE INDEX playlist_id_playlist_collaborator ON playlist.playlist_collaborator (playlist_id);

CREATE INDEX collaborator_id_playlist_collaborator ON playlist.playlist_collaborator (collaborator_id);

CREATE INDEX playlist_id_collaborator_id_playlist_collaborator
    ON playlist.playlist_collaborator (playlist_id, collaborator_id);

CREATE INDEX public_playlist_idx ON playlist.playlist (creator_id, created_for_id) WHERE public = true;

CREATE INDEX playlist_name_trgm_gin ON playlist.playlist USING GIN (name gin_trgm_ops);

CREATE INDEX playlist_description_trgm_gin ON playlist.playlist USING GIN (description gin_trgm_ops);

ALTER TABLE playlist.playlist_recording
    ADD CONSTRAINT playlist_id_foreign_key
    FOREIGN KEY (playlist_id)
    REFERENCES "playlist".playlist (id)
    ON DELETE CASCADE;

ALTER TABLE playlist.playlist_collaborator
    ADD CONSTRAINT playlist_id_foreign_key
    FOREIGN KEY (playlist_id)
    REFERENCES "playlist".playlist (id)
    ON DELETE CASCADE;

COMMIT;
