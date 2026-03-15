BEGIN;

CREATE INDEX playlist_id_collaborator_id_playlist_collaborator
    ON playlist.playlist_collaborator (playlist_id, collaborator_id);

CREATE INDEX public_playlist_idx ON playlist.playlist (creator_id, created_for_id) WHERE public = true;

COMMIT;
