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

COMMIT;
