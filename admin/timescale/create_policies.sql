SELECT add_continuous_aggregate_policy('listen_count_30day',
    start_offset => NULL,
    end_offset => 86400,
    schedule_interval => NTERVAL '1 hour');
