"""Maps request query names to their handlers."""

from listenbrainz.clickhouse.query_worker.listens import handlers

functions = {
    'clickhouse.schema.init': handlers.init_schema,
    'clickhouse.import_full_dump': handlers.import_full_dump,
    'clickhouse.import_incremental_dump': handlers.import_incremental_dump,
}
