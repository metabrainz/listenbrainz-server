BEGIN;

CREATE UNIQUE INDEX user_id_listened_at_recording_msid_ndx_listen ON listen (user_id, listened_at DESC, recording_msid);
CREATE INDEX created_ndx_listen ON listen (created);

CREATE INDEX IF NOT EXISTS listen_delete_metadata_pending_idx ON listen_delete_metadata (id) WHERE status = 'pending';

-- MBID Mapping

CREATE UNIQUE INDEX recording_msid_user_id_mbid_manual_mapping_idx ON mapping.mbid_manual_mapping(recording_msid, user_id);
CREATE UNIQUE INDEX recording_mbid_ndx_mbid_mapping_metadata ON mapping.mbid_mapping_metadata (recording_mbid);

-- these indexes are defined in mbid_mapping/mapping/mb_metadata_cache.py and created in production
-- there. this definition is only for tests and local development. remember to keep both in sync.
CREATE UNIQUE INDEX mb_metadata_cache_idx_recording_mbid ON mapping.mb_metadata_cache (recording_mbid);
CREATE UNIQUE INDEX mb_metadata_cache_idx_recording_id ON mapping.mb_metadata_cache (recording_id);
CREATE INDEX mb_metadata_cache_idx_artist_mbids ON mapping.mb_metadata_cache USING gin(artist_mbids);
CREATE INDEX mb_metadata_cache_idx_artist_ids ON mapping.mb_metadata_cache USING gin(artist_ids);
CREATE INDEX mb_metadata_cache_idx_dirty ON mapping.mb_metadata_cache (dirty);

CREATE UNIQUE INDEX mb_release_group_cache_idx_release_group_mbid ON mapping.mb_release_group_cache (release_group_mbid);
CREATE INDEX mb_release_group_cache_idx_artist_mbids ON mapping.mb_release_group_cache USING gin(artist_mbids);
CREATE INDEX mb_release_group_cache_idx_dirty ON mapping.mb_release_group_cache (dirty);

CREATE UNIQUE INDEX mb_artist_metadata_cache_idx_artist_mbid ON mapping.mb_artist_metadata_cache (artist_mbid);
CREATE INDEX mb_artist_metadata_cache_idx_dirty ON mapping.mb_artist_metadata_cache (dirty);

CREATE INDEX canonical_musicbrainz_data_idx_combined_lookup
    ON mapping.canonical_musicbrainz_data (combined_lookup);
CREATE INDEX canonical_musicbrainz_data_idx_artist_credit_recording_name
    ON mapping.canonical_musicbrainz_data (artist_credit_name, recording_name);
CREATE UNIQUE INDEX canonical_musicbrainz_data_idx_recording_mbid
    ON mapping.canonical_musicbrainz_data (recording_mbid);

CREATE INDEX can_mb_data_release_idx_combined_lookup
    ON mapping.canonical_musicbrainz_data_release_support (combined_lookup);
CREATE INDEX can_mb_data_release_idx_ac_rec_rel
    ON mapping.canonical_musicbrainz_data_release_support (artist_credit_name, recording_name, release_name);
CREATE UNIQUE INDEX can_mb_data_release_idx_recording_mbid_release_mbid
    ON mapping.canonical_musicbrainz_data_release_support (recording_mbid, release_mbid);

CREATE INDEX canonical_recording_redirect_ndx_canonical_recording_mbid
    ON mapping.canonical_recording_redirect (canonical_recording_mbid);
CREATE UNIQUE INDEX canonical_recording_redirect_ndx_recording_mbid
    ON mapping.canonical_recording_redirect (recording_mbid);

CREATE UNIQUE INDEX release_mbid_ndx_canonical_release_redirect
    ON mapping.canonical_release_redirect (release_mbid);

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

CREATE UNIQUE INDEX recording_msid_ndx_mbid_mapping ON mapping.mbid_mapping (recording_msid);
CREATE INDEX recording_mbid_ndx_mbid_mapping ON mapping.mbid_mapping (recording_mbid);
CREATE INDEX match_type_ndx_mbid_mapping ON mapping.mbid_mapping (match_type);
CREATE INDEX last_updated_ndx_mbid_mapping ON mapping.mbid_mapping (last_updated);

CREATE INDEX mbid_manual_mapping_top_idx ON mapping.mbid_manual_mapping_top (recording_msid) INCLUDE (recording_mbid);

COMMIT;
