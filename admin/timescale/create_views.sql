BEGIN;

-- TODO: Undo this
-- ALTER VIEW listen_count_week SET (timescaledb.max_interval_per_job = '31536000');

CREATE VIEW listen_count_5day
       WITH (timescaledb.continuous, timescaledb.refresh_lag=0, timescaledb.refresh_interval=900, timescaledb.max_interval_per_job = '2160000')
         AS SELECT time_bucket(bigint '432000', listened_at) AS listened_at_bucket, user_name, count(listen)
            FROM listen group by time_bucket(bigint '432000', listened_at), user_name;

-- The time_bucket definition below defines how many seconds are in a bucket and should be set to LISTEN_COUNT_BUCKET_WIDTH
-- in listenbrainz/listenstore/timescale_listenstore.py
CREATE VIEW listen_count
       WITH (timescaledb.continuous, timescaledb.refresh_lag=0, timescaledb.refresh_interval=3600)
         AS SELECT time_bucket(bigint '86400', listened_at) AS listened_at_bucket, user_name, count(listen)
            FROM listen group by time_bucket(bigint '86400', listened_at), user_name;

CREATE VIEW listened_at_max
       WITH (timescaledb.continuous, timescaledb.refresh_lag=43200, timescaledb.refresh_interval=3600)
         AS SELECT time_bucket(bigint '86400', listened_at) AS listened_at_bucket, user_name, max(listened_at) AS max_value
            FROM listen group by time_bucket(bigint '86400', listened_at), user_name;

CREATE VIEW listened_at_min
       WITH (timescaledb.continuous, timescaledb.refresh_lag=43200, timescaledb.refresh_interval=3600)
         AS SELECT time_bucket(bigint '86400', listened_at) AS listened_at_bucket, user_name, min(listened_at) AS min_value
            FROM listen group by time_bucket(bigint '86400', listened_at), user_name;

COMMIT;
