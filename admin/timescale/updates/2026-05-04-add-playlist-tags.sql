BEGIN;

CREATE TABLE IF NOT EXISTS playlist.playlist_tag (
    id SERIAL,
    playlist_id INT NOT NULL, -- FK playlist.playlist.id
    tag TEXT NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    UNIQUE (playlist_id, tag)
);

CREATE INDEX IF NOT EXISTS playlist_tag_playlist_id_idx
    ON playlist.playlist_tag (playlist_id);

CREATE INDEX IF NOT EXISTS playlist_tag_tag_idx
    ON playlist.playlist_tag (tag);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'playlist_tag_pkey'
    ) THEN
        ALTER TABLE playlist.playlist_tag ADD CONSTRAINT playlist_tag_pkey PRIMARY KEY (id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'playlist_tag_playlist_id_foreign_key'
    ) THEN
        ALTER TABLE playlist.playlist_tag
            ADD CONSTRAINT playlist_tag_playlist_id_foreign_key
            FOREIGN KEY (playlist_id)
            REFERENCES "playlist".playlist (id)
            ON DELETE CASCADE;
    END IF;
END $$;

COMMIT;

