"""Maps request query names to their handlers."""

import clickhouse.stats.handlers

functions = {
    'clickhouse.schema.init': clickhouse.stats.handlers.init_schema,
    'clickhouse.load_full_dump': clickhouse.stats.handlers.load_full_dump,
    'clickhouse.load_incremental_dump': clickhouse.stats.handlers.load_incremental_dump,
    'clickhouse.import_full_dump': clickhouse.stats.handlers.import_full_dump,
    'clickhouse.import_incremental_dump': clickhouse.stats.handlers.import_incremental_dump,
    'clickhouse.set_dump_import_state': clickhouse.stats.handlers.set_dump_import_state,
    'clickhouse.import_deleted_listens': clickhouse.stats.handlers.import_deleted_listens,
    'clickhouse.stats.hourly': clickhouse.stats.handlers.run_hourly_stats_job,
    'clickhouse.stats.full_refresh': clickhouse.stats.handlers.run_full_stats_refresh,
}
