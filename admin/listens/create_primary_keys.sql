BEGIN;

ALTER TABLE listen_delete_metadata ADD CONSTRAINT listen_delete_metadata_pkey PRIMARY KEY (id);
ALTER TABLE deleted_user_listen_history ADD CONSTRAINT deleted_user_listen_history_pkey PRIMARY KEY (id);
ALTER TABLE listen_user_metadata ADD CONSTRAINT listen_user_metadata_pkey PRIMARY KEY (user_id);

ALTER TABLE mapping.mbid_mapping_metadata ADD CONSTRAINT mbid_mapping_metadata_pkey PRIMARY KEY (recording_mbid);
ALTER TABLE mapping.mb_metadata_cache ADD CONSTRAINT mb_metadata_cache_pkey PRIMARY KEY (recording_mbid);
ALTER TABLE mapping.background_worker_state ADD CONSTRAINT background_worker_state_pkey PRIMARY KEY (key);

COMMIT;
