BEGIN;

ALTER TABLE playlist.playlist ADD CONSTRAINT playlist_pkey PRIMARY KEY (id);
ALTER TABLE playlist.playlist_recording ADD CONSTRAINT playlist_recording_pkey PRIMARY KEY (id);

COMMIT;
