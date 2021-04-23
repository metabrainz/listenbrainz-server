BEGIN;

CREATE TABLE listens_importer (
    id                          SERIAL,
    external_service_oauth_id   INTEGER,
    user_id                     INTEGER NOT NULL,
    service                     external_service_oauth_type NOT NULL,
    last_updated                TIMESTAMP WITH TIME ZONE,
    latest_listened_at          TIMESTAMP WITH TIME ZONE,
    error_message               TEXT
);

ALTER TABLE listens_importer ADD CONSTRAINT listens_importer_pkey PRIMARY KEY (id);

ALTER TABLE listens_importer
    ADD CONSTRAINT listens_importer_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

ALTER TABLE listens_importer
    ADD CONSTRAINT listens_importer_external_service_oauth_id_foreign_key
    FOREIGN KEY (external_service_oauth_id)
    REFERENCES external_service_oauth (id)
    ON DELETE SET NULL;

CREATE INDEX user_id_ndx_listens_importer ON listens_importer (user_id);
CREATE INDEX service_ndx_listens_importer ON listens_importer (service);
CREATE UNIQUE INDEX user_id_service_ndx_listens_importer ON listens_importer (user_id, service);
CREATE INDEX latest_listened_at_ndx_listens_importer ON listens_importer (latest_listened_at DESC NULLS LAST);

COMMIT;
