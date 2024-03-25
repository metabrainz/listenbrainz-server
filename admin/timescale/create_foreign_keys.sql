BEGIN;

ALTER TABLE messybrainz.submissions_redirect
    ADD CONSTRAINT messybrainz_submissions_msid_foreign_key
    FOREIGN KEY (original_msid)
    REFERENCES messybrainz.submissions (gid)
    ON DELETE NO ACTION;

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
