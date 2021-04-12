BEGIN;

CREATE TYPE external_auth_service AS ENUM ('spotify', 'youtube');

CREATE TABLE external_auth (
    id                      SERIAL,
    user_id                 INTEGER NOT NULL,
    service                 external_auth_service NOT NULL,
    access_token            TEXT NOT NULL,
    refresh_token           TEXT,
    token_expires           TIMESTAMP WITH TIME ZONE,
    last_updated            TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    record_listens          BOOLEAN NOT NULL,
    service_details         JSONB
);

ALTER TABLE external_auth ADD CONSTRAINT external_auth_pkey PRIMARY KEY (id);

ALTER TABLE external_auth
    ADD CONSTRAINT external_auth_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

COMMIT;
