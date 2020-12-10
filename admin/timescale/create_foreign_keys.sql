BEGIN;

ALTER TABLE playlist.playlist_recording
    ADD CONSTRAINT playlist_id_foreign_key
    FOREIGN KEY (playlist_id)
    REFERENCES "playlist".playlist (id)
    ON DELETE CASCADE;

COMMIT;
