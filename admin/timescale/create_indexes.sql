BEGIN;

CREATE INDEX listened_at_user_name_ndx_listen ON listen (listened_at DESC, user_name);
CREATE UNIQUE INDEX listened_at_track_name_user_name_ndx_listen ON listen (listened_at DESC, track_name, user_name);

-- This index cannot work, because the view is not materialized
--CREATE INDEX user_name_ndx_listen_count ON listen_count (user_name);

-- Use 
-- SELECT view_name, materialization_hypertable FROM timescaledb_information.continuous_aggregates;
-- to find materialized aggregates that can be used to create indexes:
--CREATE INDEX user_name_ndx_listen_count ON _timescaledb_internal._materialized_hypertable_30 (user_name);
--CREATE INDEX user_name_ndx_listened_at_max ON _timescaledb_internal._materialized_hypertable_31 (user_name);
--CREATE INDEX user_name_ndx_listened_at_min ON _timescaledb_internal._materialized_hypertable_32 (user_name);

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

COMMIT;
