BEGIN;

CREATE TYPE listen_delete_metadata_status_enum AS ENUM ('pending', 'invalid', 'complete');

CREATE TABLE listen_delete_metadata (
    id                  SERIAL                      NOT NULL,
    user_id             INTEGER                     NOT NULL,
    listened_at         TIMESTAMP WITH TIME ZONE    NOT NULL,
    recording_msid      UUID                        NOT NULL,
    status              listen_delete_metadata_status_enum NOT NULL DEFAULT 'pending',
    listen_created      TIMESTAMP WITH TIME ZONE
);

CREATE TABLE deleted_user_listen_history (
    id                          INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    user_id                     INTEGER NOT NULL,
    max_created                 TIMESTAMP WITH TIME ZONE NOT NULL
);

ALTER TABLE listen_delete_metadata
    ADD CONSTRAINT listen_delete_metadata_status_created_constraint
    CHECK ( status = 'invalid' OR status = 'pending' OR (status = 'complete' AND listen_created IS NOT NULL) );

ALTER TABLE listen_delete_metadata ADD CONSTRAINT listen_delete_metadata_pkey PRIMARY KEY (id);
ALTER TABLE deleted_user_listen_history ADD CONSTRAINT deleted_user_listen_history_pkey PRIMARY KEY (id);

CREATE INDEX listen_delete_metadata_pending_idx ON listen_delete_metadata (id) WHERE status = 'pending';

COMMIT;
