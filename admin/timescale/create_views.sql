BEGIN;

-- The time_bucket definition below defines how many seconds are in a bucket and should be set to LISTEN_COUNT_BUCKET_WIDTH
-- in listenbrainz/listenstore/timescale_listenstore.py
CREATE VIEW listen_count_5day
       WITH (timescaledb.continuous, timescaledb.refresh_lag=0, timescaledb.refresh_interval=900, timescaledb.max_interval_per_job = '2160000')
         AS SELECT time_bucket(bigint '432000', listened_at) AS listened_at_bucket, user_name, count(listen)
            FROM listen group by time_bucket(bigint '432000', listened_at), user_name;

COMMIT;
