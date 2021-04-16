BEGIN;

CREATE VIEW listen_count_30day
       WITH (timescaledb.continuous, timescaledb.refresh_lag=0, timescaledb.refresh_interval=900, timescaledb.max_interval_per_job = '5184000')
         AS SELECT time_bucket(bigint '2592000', listened_at) AS listened_at_bucket, user_name, count(listen)
            FROM listen group by time_bucket(bigint '2592000', listened_at), user_name;

COMMIT;
