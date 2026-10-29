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

-- messybrainz
CREATE UNIQUE INDEX messybrainz_gid_ndx ON messybrainz.submissions (gid);
-- can't use a single index here because some values in these columns are too large and exceed the max
-- index size allowed when used together.
CREATE INDEX messybrainz_recording_ndx ON messybrainz.submissions (lower(recording));
CREATE INDEX messybrainz_artist_credit_ndx ON messybrainz.submissions (lower(artist_credit));
CREATE INDEX messybrainz_release_ndx ON messybrainz.submissions (lower(release));
CREATE INDEX messybrainz_track_number_ndx ON messybrainz.submissions (lower(track_number));
CREATE INDEX messybrainz_duration_ndx ON messybrainz.submissions (duration);

CREATE UNIQUE INDEX messybrainz_redirect_gid_ndx ON messybrainz.submissions_redirect (duplicate_msid);

ALTER TABLE messybrainz.submissions_redirect
    ADD CONSTRAINT messybrainz_submissions_msid_foreign_key
    FOREIGN KEY (original_msid)
    REFERENCES messybrainz.submissions (gid)
    ON DELETE NO ACTION;

CREATE INDEX popularity_recording_listen_count_idx ON popularity.recording (total_listen_count) INCLUDE (recording_mbid);
CREATE INDEX popularity_recording_user_count_idx ON popularity.recording (total_user_count) INCLUDE (recording_mbid);

CREATE INDEX popularity_artist_listen_count_idx ON popularity.artist (total_listen_count) INCLUDE (artist_mbid);
CREATE INDEX popularity_artist_user_count_idx ON popularity.artist (total_user_count) INCLUDE (artist_mbid);

CREATE INDEX popularity_release_listen_count_idx ON popularity.release (total_listen_count) INCLUDE (release_mbid);
CREATE INDEX popularity_release_user_count_idx ON popularity.release (total_user_count) INCLUDE (release_mbid);

CREATE INDEX popularity_top_recording_artist_mbid_listen_count_idx ON popularity.top_recording (artist_mbid, total_listen_count) INCLUDE (recording_mbid);
CREATE INDEX popularity_top_recording_artist_mbid_user_count_idx ON popularity.top_recording (artist_mbid, total_user_count) INCLUDE (recording_mbid);

CREATE INDEX popularity_top_release_artist_mbid_listen_count_idx ON popularity.top_release (artist_mbid, total_listen_count) INCLUDE (release_mbid);
CREATE INDEX popularity_top_release_artist_mbid_user_count_idx ON popularity.top_release (artist_mbid, total_user_count) INCLUDE (release_mbid);

CREATE UNIQUE INDEX similar_recordings_dev_uniq_idx ON similarity.recording_dev (mbid0, mbid1);
CREATE UNIQUE INDEX similar_recordings_dev_reverse_uniq_idx ON similarity.recording_dev (mbid1, mbid0);
CREATE INDEX similar_recordings_algorithm_dev_idx ON similarity.recording_dev USING gin (metadata);

CREATE UNIQUE INDEX similar_artist_credit_mbids_dev_uniq_idx ON similarity.artist_credit_mbids_dev (mbid0, mbid1);
CREATE UNIQUE INDEX similar_artist_credit_mbids_dev_reverse_uniq_idx ON similarity.artist_credit_mbids_dev (mbid1, mbid0);
CREATE INDEX similar_artist_credit_mbids_algorithm_dev_idx ON similarity.artist_credit_mbids_dev USING gin (metadata);

-- NOTE: If the indexes for the recording_prod/artist_credit_mbids_prod table changes, update the code in listenbrainz/db/similarity.py !
CREATE UNIQUE INDEX similar_recordings_uniq_idx ON similarity.recording (mbid0, mbid1);
CREATE UNIQUE INDEX similar_recordings_reverse_uniq_idx ON similarity.recording (mbid1, mbid0);

CREATE UNIQUE INDEX similar_artist_credit_mbids_uniq_idx ON similarity.artist_credit_mbids (mbid0, mbid1);
CREATE UNIQUE INDEX similar_artist_credit_mbids_reverse_uniq_idx ON similarity.artist_credit_mbids (mbid1, mbid0);

CREATE INDEX similarity_overhyped_artists_artist_mbid_idx ON similarity.overhyped_artists(artist_mbid) INCLUDE (factor);

CREATE UNIQUE INDEX year_in_music_cover_user_id_idx ON statistics.year_in_music_cover (user_id, year);

CREATE INDEX tags_lb_tag_radio_percent_idx ON tags.lb_tag_radio (tag, percent) INCLUDE (source, recording_mbid, tag_count);

COMMIT;
