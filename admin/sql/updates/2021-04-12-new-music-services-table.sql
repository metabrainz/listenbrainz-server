BEGIN;

CREATE TYPE external_service_oauth_type AS ENUM ('spotify', 'youtube');

CREATE TABLE external_service_oauth (
    id                      SERIAL,
    user_id                 INTEGER NOT NULL,
    service                 external_service_oauth_type NOT NULL,
    access_token            TEXT NOT NULL,
    refresh_token           TEXT,
    token_expires           TIMESTAMP WITH TIME ZONE,
    last_updated            TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    record_listens          BOOLEAN NOT NULL,
    service_details         JSONB
);

ALTER TABLE external_service_oauth ADD CONSTRAINT external_service_oauth_pkey PRIMARY KEY (id);

ALTER TABLE external_service_oauth
    ADD CONSTRAINT external_service_oauth_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

CREATE INDEX user_id_ndx_external_service_oauth ON external_service_oauth (user_id);
CREATE INDEX service_ndx_external_service_oauth ON external_service_oauth (service);
CREATE UNIQUE INDEX user_id_service_ndx_external_service_oauth ON external_service_oauth (user_id, service);

COMMIT;
