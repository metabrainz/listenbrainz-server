BEGIN;

CREATE TABLE listen (
        listened_at     BIGINT                   NOT NULL,
        recording_msid  UUID                     NOT NULL,
        user_name       TEXT                     NOT NULL,
        created         TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        data            JSONB                    NOT NULL
);

-- 86400 * 5 seconds = 43200
SELECT create_hypertable('listen', 'listened_at', chunk_time_interval => 432000);

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO timescale_lb;

COMMIT;
