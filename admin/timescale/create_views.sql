BEGIN;

CREATE VIEW listen_count
       WITH (timescaledb.continuous, timescaledb.refresh_lag=43200, timescaledb.refresh_interval=3600)
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
