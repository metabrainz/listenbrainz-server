-- Listens are hash-partitioned by user_id. Partitions are created by `manage.py migrate_listens
-- create-schema`, indexes by `manage.py migrate_listens create-indexes` (see create_indexes.sql).
BEGIN;

CREATE TABLE listen (
    listened_at     TIMESTAMP WITH TIME ZONE NOT NULL,
    created         TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    user_id         INTEGER                  NOT NULL,
    recording_msid  UUID                     NOT NULL,
    data            JSONB                    NOT NULL
) PARTITION BY HASH (user_id);

COMMIT;
