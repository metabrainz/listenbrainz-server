BEGIN;

CREATE INDEX listened_at_user_id_ndx_listen ON listen (listened_at DESC, user_id);
CREATE INDEX created_ndx_listen ON listen (created);
CREATE UNIQUE INDEX listened_at_user_id_recording_msid_ndx_listen ON listen (listened_at DESC, user_id, recording_msid);

CREATE INDEX recording_msid_ndx_listen on listen (recording_msid);

CREATE UNIQUE INDEX user_id_ndx_listen_user_metadata ON listen_user_metadata (user_id);

-- View indexes are created in listenbrainz/db/timescale.py

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

-- Internet Archive indexes
CREATE UNIQUE INDEX internetarchive_cache_track_track_id_idx ON internetarchive_cache.track (track_id);
CREATE INDEX internetarchive_cache_track_artist_gin_idx ON internetarchive_cache.track USING GIN (artist);
CREATE INDEX internetarchive_cache_track_name_idx ON internetarchive_cache.track (name);
CREATE INDEX internetarchive_cache_track_album_idx ON internetarchive_cache.track (album);
CREATE INDEX internetarchive_cache_track_stream_urls_gin_idx ON internetarchive_cache.track USING GIN (stream_urls);
CREATE INDEX internetarchive_cache_track_last_updated_idx ON internetarchive_cache.track (last_updated);


CREATE INDEX tags_lb_tag_radio_percent_idx ON tags.lb_tag_radio (tag, percent) INCLUDE (source, recording_mbid, tag_count);

COMMIT;
