BEGIN;

ALTER TABLE playlist.playlist ADD CONSTRAINT playlist_pkey PRIMARY KEY (id);
ALTER TABLE playlist.playlist_recording ADD CONSTRAINT playlist_recording_pkey PRIMARY KEY (id);
ALTER TABLE mbid_mapping_metadata ADD CONSTRAINT mbid_mapping_metadata_pkey PRIMARY KEY (recording_mbid);
ALTER TABLE mapping.mb_metadata_cache ADD CONSTRAINT mb_metadata_cache_pkey PRIMARY KEY (recording_mbid);
ALTER TABLE background_worker_state ADD CONSTRAINT background_worker_state_pkey PRIMARY KEY (key);

COMMIT;
