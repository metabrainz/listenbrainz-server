"""Maps request query names to their handlers."""

from listenbrainz.clickhouse.query_worker.daily_activity import daily_activity
from listenbrainz.clickhouse.query_worker.listening_activity import listening_activity
from listenbrainz.clickhouse.query_worker.listens import handlers
from listenbrainz.clickhouse.query_worker.metadata_cache import update_metadata_cache

functions = {
    'clickhouse.listening_activity': listening_activity,
    'clickhouse.daily_activity': daily_activity,
    'clickhouse.schema.init': handlers.init_schema,
    'clickhouse.update_metadata_cache': update_metadata_cache,
    'clickhouse.import_full_dump': handlers.import_full_dump,
    'clickhouse.import_incremental_dump': handlers.import_incremental_dump,
}
