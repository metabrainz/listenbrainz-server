-- 2592000 is number of seconds in 30 days
CREATE MATERIALIZED VIEW listen_count_30day WITH (timescaledb.continuous) AS SELECT time_bucket(bigint '2592000', listened_at) AS listened_at_bucket, user_name, count(listen) FROM listen GROUP BY listened_at_bucket, user_name;
