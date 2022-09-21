BEGIN;

ALTER TABLE playlist.playlist ADD CONSTRAINT playlist_pkey PRIMARY KEY (id);
ALTER TABLE playlist.playlist_recording ADD CONSTRAINT playlist_recording_pkey PRIMARY KEY (id);
ALTER TABLE mapping.mb_metadata_cache ADD CONSTRAINT mb_metadata_cache_pkey PRIMARY KEY (recording_mbid);

COMMIT;
