BEGIN;

CREATE INDEX listened_at_user_name_ndx_listen ON listen (listened_at DESC, user_name);
CREATE INDEX created_user_name_ndx_listen ON listen (created);
CREATE UNIQUE INDEX listened_at_track_name_user_name_ndx_listen ON listen (listened_at DESC, track_name, user_name);

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

CREATE UNIQUE INDEX id_ndx_listen_join_listen_mbid_mapping ON listen_mbid_mapping (id);
CREATE UNIQUE INDEX recording_msid_ndx_listen_join_listen_mbid_mapping ON listen_join_listen_mbid_mapping (recording_msid);

COMMIT;
