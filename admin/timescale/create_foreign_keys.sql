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

ALTER TABLE mbid_mapping
    ADD CONSTRAINT mbid_mapping_recording_mbid_foreign_key
    FOREIGN KEY (recording_mbid)
    REFERENCES mbid_mapping_metadata (recording_mbid)
    ON DELETE CASCADE;

COMMIT;
