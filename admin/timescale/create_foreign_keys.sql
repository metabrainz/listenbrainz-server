BEGIN;

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

ALTER TABLE listen_join_listen_mbid_mapping
    ADD CONSTRAINT listen_mbid_mapping_foreign_key
    FOREIGN KEY (listen_mbid_mapping)
    REFERENCES listen_mbid_mapping (id)
    ON DELETE CASCADE;

COMMIT;
