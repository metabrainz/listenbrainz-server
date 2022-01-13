BEGIN;

CREATE INDEX listened_at_user_id_ndx_listen ON listen (listened_at DESC, user_id);
CREATE INDEX created_ndx_listen ON listen (created);
CREATE UNIQUE INDEX listened_at_track_name_user_id_ndx_listen ON listen (listened_at DESC, track_name, user_id);

CREATE UNIQUE INDEX user_id_ndx_listen_count ON listen_count (user_id);

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

CREATE UNIQUE INDEX recording_mbid_ndx_mbid_mapping_metadata ON mbid_mapping_metadata (recording_mbid);

CREATE UNIQUE INDEX recording_msid_ndx_mbid_mapping ON mbid_mapping (recording_msid);
CREATE INDEX recording_mbid_ndx_mbid_mapping ON mbid_mapping (recording_mbid);
CREATE INDEX match_type_ndx_mbid_mapping ON mbid_mapping (match_type);
CREATE INDEX last_updated_ndx_mbid_mapping ON mbid_mapping (last_updated);

COMMIT;
