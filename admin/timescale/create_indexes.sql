BEGIN;

CREATE INDEX listened_at_user_id_ndx_listen ON listen (listened_at DESC, user_id);
CREATE INDEX created_ndx_listen ON listen (created);
CREATE UNIQUE INDEX listened_at_user_id_recording_msid_ndx_listen ON listen (listened_at DESC, user_id, recording_msid);

CREATE INDEX recording_msid_ndx_listen on listen (recording_msid);

CREATE UNIQUE INDEX user_id_ndx_listen_user_metadata ON listen_user_metadata (user_id);

-- View indexes are created in listenbrainz/db/timescale.py

-- Playlists

CREATE UNIQUE INDEX mbid_playlist ON playlist.playlist (mbid);
CREATE INDEX creator_id_playlist ON playlist.playlist (creator_id);
CREATE INDEX copied_from_id_playlist ON playlist.playlist (copied_from_id);
CREATE INDEX created_for_id_playlist ON playlist.playlist (created_for_id);

CREATE INDEX playlist_id_playlist_recording ON playlist.playlist_recording (playlist_id);
CREATE INDEX mbid_playlist_recording ON playlist.playlist_recording (mbid);
CREATE INDEX added_by_id_playlist_recording ON playlist.playlist_recording (added_by_id);

CREATE INDEX playlist_id_playlist_collaborator ON playlist.playlist_collaborator (playlist_id);
CREATE INDEX collaborator_id_playlist_collaborator ON playlist.playlist_collaborator (collaborator_id);

-- MBID Mapping

CREATE UNIQUE INDEX recording_msid_user_id_mbid_manual_mapping_idx ON mbid_manual_mapping(recording_msid, user_id);
CREATE UNIQUE INDEX recording_mbid_ndx_mbid_mapping_metadata ON mbid_mapping_metadata (recording_mbid);

-- these indexes are defined in listenbrainz/mbid_mapping/mapping/mb_metadata_cache.py and created in production
-- there. this definition is only for tests and local development. remember to keep both in sync.
CREATE UNIQUE INDEX mb_metadata_cache_idx_recording_mbid ON mapping.mb_metadata_cache (recording_mbid);
CREATE INDEX mb_metadata_cache_idx_artist_mbids ON mapping.mb_metadata_cache USING gin(artist_mbids);
CREATE INDEX mb_metadata_cache_idx_dirty ON mapping.mb_metadata_cache (dirty);

CREATE UNIQUE INDEX recording_msid_ndx_mbid_mapping ON mbid_mapping (recording_msid);
CREATE INDEX recording_mbid_ndx_mbid_mapping ON mbid_mapping (recording_mbid);
CREATE INDEX match_type_ndx_mbid_mapping ON mbid_mapping (match_type);
CREATE INDEX last_updated_ndx_mbid_mapping ON mbid_mapping (last_updated);

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

CREATE UNIQUE INDEX spotify_cache_album_spotify_id_idx ON spotify_cache.album (album_id);
CREATE UNIQUE INDEX spotify_cache_artist_spotify_id_idx ON spotify_cache.artist (artist_id);
CREATE UNIQUE INDEX spotify_cache_track_spotify_id_idx ON spotify_cache.track (track_id);
CREATE INDEX spotify_cache_rel_album_artist_track_id_idx ON spotify_cache.rel_album_artist (album_id);
CREATE INDEX spotify_cache_rel_track_artist_track_id_idx ON spotify_cache.rel_track_artist (track_id);

CREATE UNIQUE INDEX apple_cache_album_apple_id_idx ON apple_cache.album (album_id);
CREATE UNIQUE INDEX apple_cache_artist_apple_id_idx ON apple_cache.artist (artist_id);
CREATE UNIQUE INDEX apple_cache_track_apple_id_idx ON apple_cache.track (track_id);
CREATE INDEX apple_cache_rel_album_artist_track_id_idx ON apple_cache.rel_album_artist (album_id);
CREATE INDEX apple_cache_rel_track_artist_track_id_idx ON apple_cache.rel_track_artist (track_id);

CREATE UNIQUE INDEX soundcloud_cache_track_soundcloud_id_idx ON soundcloud_cache.track (track_id);
CREATE UNIQUE INDEX soundcloud_cache_artist_soundcloud_id_idx ON soundcloud_cache.artist (artist_id);

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

CREATE INDEX mbid_manual_mapping_top_idx ON mbid_manual_mapping_top (recording_msid) INCLUDE (recording_mbid);

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

CREATE INDEX tags_lb_tag_radio_percent_idx ON tags.lb_tag_radio (tag, percent) INCLUDE (source, recording_mbid, tag_count);

COMMIT;
