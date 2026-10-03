BEGIN;

DELETE FROM listen                      CASCADE;
DELETE FROM listen_user_metadata        CASCADE;
DELETE FROM messybrainz.submissions     CASCADE;
DELETE FROM playlist.playlist           CASCADE;

DELETE FROM spotify_cache.rel_album_artist;
DELETE FROM spotify_cache.rel_track_artist;
DELETE FROM spotify_cache.artist;
DELETE FROM spotify_cache.track;
DELETE FROM spotify_cache.album;

DELETE FROM internetarchive_cache.track;

COMMIT;
