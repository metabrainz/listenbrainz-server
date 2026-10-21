-- Add foreign keys from the playlist tables to "user" now that both live in the main database.
-- Run this after the playlist data has been copied from Timescale (see 2026-09-29-playlists.sql).
-- Timescale could not enforce these references, so first remove rows that point to deleted users,
-- matching what ON DELETE CASCADE would have done had the constraints existed.
BEGIN;

DELETE FROM playlist.playlist p
      WHERE NOT EXISTS (SELECT 1 FROM "user" u WHERE u.id = p.creator_id)
         OR (p.created_for_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM "user" u WHERE u.id = p.created_for_id));

DELETE FROM playlist.playlist_collaborator pc
      WHERE NOT EXISTS (SELECT 1 FROM "user" u WHERE u.id = pc.collaborator_id);

DELETE FROM playlist.playlist_recording pr
      WHERE NOT EXISTS (SELECT 1 FROM "user" u WHERE u.id = pr.added_by_id);

ALTER TABLE playlist.playlist
    ADD CONSTRAINT playlist_creator_id_foreign_key
    FOREIGN KEY (creator_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

ALTER TABLE playlist.playlist
    ADD CONSTRAINT playlist_created_for_id_foreign_key
    FOREIGN KEY (created_for_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

ALTER TABLE playlist.playlist_collaborator
    ADD CONSTRAINT playlist_collaborator_id_foreign_key
    FOREIGN KEY (collaborator_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

ALTER TABLE playlist.playlist_recording
    ADD CONSTRAINT playlist_recording_added_by_id_foreign_key
    FOREIGN KEY (added_by_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

COMMIT;
