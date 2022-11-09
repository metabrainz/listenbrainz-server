BEGIN;

ALTER TABLE playlist.playlist RENAME COLUMN algorithm_metadata TO additional_metadata;
ALTER TABLE playlist.playlist_recording ADD COLUMN additional_metadata JSONB;

UPDATE playlist.playlist SET additional_metadata = jsonb_build_object('algorithm_metadata', additional_metadata);

COMMIT;
