BEGIN;

CREATE UNIQUE INDEX user_id_listened_at_recording_msid_ndx_listen ON listen (user_id, listened_at DESC, recording_msid);
CREATE INDEX created_ndx_listen ON listen (created);

CREATE INDEX IF NOT EXISTS listen_delete_metadata_pending_idx ON listen_delete_metadata (id) WHERE status = 'pending';

-- Spotify, Apple Music and SoundCloud metadata indexes

CREATE INDEX spotify_metadata_index_idx_combined_lookup_all
    ON mapping.spotify_metadata_index (combined_lookup_all);
CREATE INDEX spotify_metadata_index_idx_combined_lookup_without_album
    ON mapping.spotify_metadata_index (combined_lookup_without_album);

CREATE INDEX apple_metadata_index_idx_combined_lookup_all
    ON mapping.apple_metadata_index (combined_lookup_all);
CREATE INDEX apple_metadata_index_idx_combined_lookup_without_album
    ON mapping.apple_metadata_index (combined_lookup_without_album);

CREATE INDEX soundcloud_metadata_index_idx_combined_lookup
    ON mapping.soundcloud_metadata_index (combined_lookup_without_album);

COMMIT;
