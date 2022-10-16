-- run after the migration script for porting the existing data to normalized tables has run
BEGIN;

ALTER TABLE spotify_cache.raw_cache_data SET LOGGED;
ALTER TABLE spotify_cache.album SET LOGGED;
ALTER TABLE spotify_cache.artist SET LOGGED;
ALTER TABLE spotify_cache.track SET LOGGED;
ALTER TABLE spotify_cache.rel_album_artist SET LOGGED;
ALTER TABLE spotify_cache.rel_track_artist SET LOGGED;

CREATE UNIQUE INDEX spotify_metadata_cache_album_id_ndx ON spotify_cache.raw_cache_data (album_id);
CREATE UNIQUE INDEX spotify_cache_album_spotify_id_idx ON spotify_cache.album (spotify_id);
CREATE UNIQUE INDEX spotify_cache_artist_spotify_id_idx ON spotify_cache.artist (spotify_id);
CREATE UNIQUE INDEX spotify_cache_track_spotify_id_idx ON spotify_cache.track (spotify_id);
CREATE INDEX spotify_cache_rel_album_artist_track_id_idx ON spotify_cache.rel_album_artist (album_id);
CREATE INDEX spotify_cache_rel_track_artist_track_id_idx ON spotify_cache.rel_track_artist (track_id);

COMMIT;
