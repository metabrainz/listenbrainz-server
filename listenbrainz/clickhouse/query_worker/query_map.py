"""Maps request query names to their handlers."""

from listenbrainz.clickhouse.query_worker.daily_activity import daily_activity
from listenbrainz.clickhouse.query_worker.listens import handlers

functions = {
    'clickhouse.daily_activity': daily_activity,
    'clickhouse.schema.init': handlers.init_schema,
    'clickhouse.import_full_dump': handlers.import_full_dump,
    'clickhouse.import_incremental_dump': handlers.import_incremental_dump,
}
