BEGIN;

ALTER TABLE playlist.playlist ADD CONSTRAINT playlist_pkey PRIMARY KEY (id);
ALTER TABLE playlist.playlist_recording ADD CONSTRAINT playlist_recording_pkey PRIMARY KEY (id);
ALTER TABLE mbid_mapping_metadata ADD CONSTRAINT mbid_mapping_metadata_pkey PRIMARY KEY (recording_mbid);

COMMIT;
