BEGIN;

CREATE TABLE IF NOT EXISTS playlist.playlist_tag (
    id serial,
    playlist_id int not null,  -- FK playlist.playlist.id
    tag text not null,
    created timestamp with time zone default now() not null,
    UNIQUE (playlist_id, tag)
);

ALTER TABLE playlist.playlist_tag ADD CONSTRAINT playlist_tag_pkey PRIMARY KEY (id);

CREATE INDEX playlist_tag_playlist_id_idx ON playlist.playlist_tag (playlist_id);

CREATE INDEX playlist_tag_tag_idx ON playlist.playlist_tag (tag);

ALTER TABLE playlist.playlist_tag
    ADD CONSTRAINT playlist_tag_playlist_id_foreign_key
    FOREIGN KEY (playlist_id)
    REFERENCES "playlist".playlist (id)
    ON DELETE CASCADE;

COMMIT;
