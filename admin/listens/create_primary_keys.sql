BEGIN;

ALTER TABLE listen_delete_metadata ADD CONSTRAINT listen_delete_metadata_pkey PRIMARY KEY (id);
ALTER TABLE deleted_user_listen_history ADD CONSTRAINT deleted_user_listen_history_pkey PRIMARY KEY (id);
ALTER TABLE listen_user_metadata ADD CONSTRAINT listen_user_metadata_pkey PRIMARY KEY (user_id);

COMMIT;
