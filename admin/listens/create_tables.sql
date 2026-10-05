-- Listens are hash-partitioned by user_id. The table, partitions and indexes are created
-- by `manage.py init_listens_db` (see also create_indexes.sql).
BEGIN;

CREATE TABLE listen (
    listened_at     TIMESTAMP WITH TIME ZONE NOT NULL,
    created         TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    user_id         INTEGER                  NOT NULL,
    recording_msid  UUID                     NOT NULL,
    data            JSONB                    NOT NULL
) PARTITION BY HASH (user_id);

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

COMMIT;
