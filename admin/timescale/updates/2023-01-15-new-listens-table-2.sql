BEGIN;

ALTER TABLE listen RENAME TO listen_old;
ALTER TABLE listen_new RENAME TO listen;

-- alter columns of listen user metadata and listen delete metadata
ALTER TABLE listen_user_metadata
    ALTER COLUMN min_listened_at TYPE TIMESTAMP WITH TIME ZONE USING to_timestamp(min_listened_at),
    ALTER COLUMN max_listened_at TYPE TIMESTAMP WITH TIME ZONE USING to_timestamp(max_listened_at);

ALTER TABLE listen_delete_metadata
    ALTER COLUMN listened_at TYPE TIMESTAMP WITH TIME ZONE USING to_timestamp(listened_at);

COMMIT;
