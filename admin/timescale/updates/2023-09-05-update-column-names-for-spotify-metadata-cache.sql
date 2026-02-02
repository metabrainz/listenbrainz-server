BEGIN;

ALTER TABLE spotify_cache.album RENAME COLUMN spotify_id TO album_id;
ALTER TABLE spotify_cache.artist RENAME COLUMN spotify_id TO artist_id;
ALTER TABLE spotify_cache.track RENAME COLUMN spotify_id TO track_id;

COMMIT;
