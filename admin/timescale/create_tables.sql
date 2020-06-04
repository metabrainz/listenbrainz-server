BEGIN;

CREATE TABLE listen (
        listened_at     BIGINT                   NOT NULL,
        track_name      TEXT                     NOT NULL,
        user_name       TEXT                     NOT NULL,
        created         TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        data            JSONB                    NOT NULL
);

-- 86400 seconds * 5 = 432000 seconds = 5 days
SELECT create_hypertable('listen', 'listened_at', chunk_time_interval => 432000);

COMMIT;
