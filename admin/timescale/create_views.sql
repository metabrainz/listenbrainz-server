-- 2592000 is number of seconds in 30 days
CREATE MATERIALIZED VIEW listen_count_30day WITH (timescaledb.continuous) AS SELECT time_bucket(bigint '2592000', listened_at) AS listened_at_bucket, user_name, count(listen) FROM listen GROUP BY listened_at_bucket, user_name;

-- Add a policy to keep the listen_count_30day up to date
SELECT add_continuous_aggregate_policy('listen_count_30day',
    start_offset => NULL,
    end_offset => 86400,
    schedule_interval => INTERVAL '1 hour');
