BEGIN;

CREATE VIEW listen_count
       WITH (timescaledb.continuous, timescaledb.refresh_lag=43200, timescaledb.refresh_interval=3600)
         AS SELECT time_bucket(bigint '86400', listened_at) AS bucket, user_name, count(listen)
            FROM listen group by time_bucket(bigint '86400', listened_at), user_name;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO listenbrainz_ts;

COMMIT;
