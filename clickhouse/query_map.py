"""
ClickHouse Query Map

Maps query names to handler functions for the ClickHouse request consumer.
"""

import clickhouse.stats.handlers

functions = {
    'clickhouse.load_full_dump': clickhouse.stats.handlers.load_full_dump,
    'clickhouse.load_incremental_dump': clickhouse.stats.handlers.load_incremental_dump,
    'clickhouse.import_full_dump': clickhouse.stats.handlers.import_full_dump,
    'clickhouse.import_incremental_dump': clickhouse.stats.handlers.import_incremental_dump,
    'clickhouse.stats.hourly': clickhouse.stats.handlers.run_hourly_stats_job,
    'clickhouse.stats.full_refresh': clickhouse.stats.handlers.run_full_stats_refresh,
    'clickhouse.stats.cleanup_deletions': clickhouse.stats.handlers.cleanup_old_deletions,
}


def get_query_handler(query):
    """Get the handler function for a query."""
    return functions[query]
