BEGIN;

CREATE INDEX listened_at_user_id_ndx_listen ON listen (listened_at DESC, user_id);
CREATE INDEX created_ndx_listen ON listen (created);

CREATE UNIQUE INDEX listened_at_track_name_user_id_ndx_listen ON listen (listened_at DESC, track_name, user_id);

CREATE INDEX recording_msid_ndx_listen on listen ((data->'track_metadata'->'additional_info'->>'recording_msid'));

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

CREATE UNIQUE INDEX spotify_metadata_cache_album_id_ndx ON spotify_cache.raw_cache_data (album_id);
CREATE UNIQUE INDEX spotify_cache_album_spotify_id_idx ON spotify_cache.album (spotify_id);
CREATE UNIQUE INDEX spotify_cache_artist_spotify_id_idx ON spotify_cache.artist (spotify_id);
CREATE UNIQUE INDEX spotify_cache_track_spotify_id_idx ON spotify_cache.track (spotify_id);
CREATE INDEX spotify_cache_rel_album_artist_track_id_idx ON spotify_cache.rel_album_artist (album_id);
CREATE INDEX spotify_cache_rel_track_artist_track_id_idx ON spotify_cache.rel_track_artist (track_id);

CREATE UNIQUE INDEX similar_recordings_uniq_idx ON similarity.recording (mbid0, mbid1);
CREATE UNIQUE INDEX similar_recordings_reverse_uniq_idx ON similarity.recording (mbid1, mbid0);
CREATE INDEX similar_recordings_algorithm_idx ON similarity.recording USING gin (metadata);

CREATE UNIQUE INDEX similar_artists_uniq_idx ON similarity.artist_credit_mbids (mbid0, mbid1);
CREATE UNIQUE INDEX similar_artist_credit_mbids_reverse_uniq_idx ON similarity.artist_credit_mbids (mbid1, mbid0);
CREATE INDEX similar_artist_credit_mbids_algorithm_idx ON similarity.artist_credit_mbids USING gin (metadata);

CREATE INDEX mbid_manual_mapping_top_idx ON mbid_manual_mapping_top (recording_msid) INCLUDE (recording_mbid);

COMMIT;
