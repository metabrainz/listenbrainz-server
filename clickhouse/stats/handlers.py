"""Handlers for the requests of the ClickHouse request consumer (see query_map)."""

import logging
from contextlib import closing
from typing import Callable, Iterator, Optional

from clickhouse import config
from clickhouse.client import ClickHouseConnection
from clickhouse.stats.activity_cache_manager import (
    ACTIVITY_STAT_TYPES,
    ActivityStatsCacheManager,
    BulkActivityStatsCacheManager,
)
from clickhouse.stats.cache_manager import StatsCacheManager
from clickhouse.stats.deleted_listens import import_deleted_listens as _import_deleted_listens
from clickhouse.stats.ftp import DumpType
from clickhouse.stats.import_state import INCREMENTAL_DUMP_STATE, set_import_state
from clickhouse.stats.load_dump import describe_load_errors, import_missing_incremental_dumps, load_dump, load_from_ftp
from clickhouse.stats.schema import ensure_stats_schema

logger = logging.getLogger(__name__)

# Every user stat type the ClickHouse pipeline computes.
STAT_TYPES = ACTIVITY_STAT_TYPES


def _stats_manager(connection: ClickHouseConnection, stat_type: str, *, full: bool = False):
    manager_class = BulkActivityStatsCacheManager if full else ActivityStatsCacheManager
    return manager_class(connection, stat_type)


def _client():
    return closing(ClickHouseConnection.from_config().connect())


def _error(message_type: str, error: Exception, **fields) -> list[dict]:
    """Log a failed request and return the error result message for it."""
    logger.error("%s failed: %s", message_type, error, exc_info=True)
    return [{'type': message_type, 'status': 'error', 'error': str(error), **fields}]


def _raise_on_load_errors(result: dict) -> None:
    if result['errors']:
        raise RuntimeError(describe_load_errors(result['errors']))


def _dump_imported(dump_type: str, result: dict, **fields) -> dict:
    return {
        'type': 'clk_dump_imported',
        'dump_type': dump_type,
        'status': 'success',
        'dump_id': result.get('dump_id'),
        'total_inserted': result['total_inserted'],
        'files_completed': result['files_completed'],
        **fields,
    }


def _load_dump_from_path(dump_path: str, dump_type: DumpType, workers: int = 4) -> list[dict]:
    """Load a directory of Parquet files into the ClickHouse listens table."""
    try:
        result = load_dump(dump_path, ClickHouseConnection.from_config(), dump_type, workers)
        _raise_on_load_errors(result)
    except Exception as e:
        return _error('clk_dump_imported', e, dump_type=dump_type.value)
    return [_dump_imported(dump_type.value, result, dump_path=dump_path)]


def load_full_dump(dump_path: str, workers: int = 4) -> list[dict]:
    """Load a full Parquet dump directory, replacing listens."""
    return _load_dump_from_path(dump_path, DumpType.FULL, workers)


def load_incremental_dump(dump_path: str, workers: int = 4) -> list[dict]:
    """Load an incremental Parquet dump directory into ClickHouse listens table."""
    return _load_dump_from_path(dump_path, DumpType.INCREMENTAL, workers)


def init_schema() -> list[dict]:
    """Create the ClickHouse stats schema."""
    try:
        with _client() as ch_client:
            ensure_stats_schema(ch_client)
    except Exception as e:
        return _error('clk_schema_initialized', e)
    return [{'type': 'clk_schema_initialized', 'status': 'success'}]


def import_full_dump(workers: int = 4) -> list[dict]:
    """Download the latest full dump from FTP and load it, replacing listens."""
    try:
        result = load_from_ftp(DumpType.FULL, ClickHouseConnection.from_config(), workers=workers)
        _raise_on_load_errors(result)
    except Exception as e:
        return _error('clk_dump_imported', e, dump_type='full')
    return [_dump_imported('full', result)]


def import_incremental_dump(workers: int = 4, max_dumps: Optional[int] = None) -> list[dict]:
    """Import the incremental dumps on FTP that are not loaded yet, oldest first.

    Stops at the first failure so that dump is retried next run. ``max_dumps`` limits how
    many are loaded in this run.
    """
    try:
        result = import_missing_incremental_dumps(
            ClickHouseConnection.from_config(), workers=workers, max_dumps=max_dumps,
        )
    except Exception as e:
        return _error('clk_dump_imported', e, dump_type='incremental')

    pending = result['pending']
    messages = [_dump_imported('incremental', dump, pending=pending) for dump in result['imported']]
    messages.extend({
        'type': 'clk_dump_imported', 'dump_type': 'incremental', 'status': 'error',
        'dump_id': dump_id, 'pending': pending, 'error': error,
    } for dump_id, error in result['errors'])

    if not messages:
        logger.info("No incremental dumps to import")
    return messages


def set_dump_import_state(dump_id: int) -> list[dict]:
    """Set the incremental dump mark: the next catch-up loads the dumps after ``dump_id``."""
    try:
        with _client() as ch_client:
            ensure_stats_schema(ch_client)
            set_import_state(ch_client, INCREMENTAL_DUMP_STATE, dump_id)
    except Exception as e:
        return _error('clk_dump_import_state_set', e, dump_id=dump_id)
    return [{'type': 'clk_dump_import_state_set', 'status': 'success', 'dump_id': dump_id}]


def import_deleted_listens(batch_size: int = 10_000) -> list[dict]:
    """Import listen deletions from the listens database and apply them."""
    try:
        if not config.LISTENS_DSN:
            raise ValueError("LISTENS_DSN is not configured")
        with _client() as ch_client:
            summary = _import_deleted_listens(config.LISTENS_DSN, ch_client, batch_size=batch_size)
    except Exception as e:
        return _error('clk_deleted_listens_imported', e)
    return [{'type': 'clk_deleted_listens_imported', 'status': 'success', **summary}]


def _run_stats_job(
    job: str,
    entity: Optional[str],
    run: Callable[[StatsCacheManager], Iterator[dict]],
) -> Iterator[dict]:
    """Yield the messages of ``run`` for the manager of ``entity``, or of every stat type.

    A failing stat type yields a clk_stats_error message without stopping the others.
    """
    if entity and entity not in STAT_TYPES:
        yield {'type': 'clk_stats_error', 'entity': entity, 'job': job, 'error': f"Unknown entity: {entity}"}
        return
    entities_to_process = [entity] if entity else list(STAT_TYPES)
    logger.info("Running %s stats job for entities: %s", job, entities_to_process)

    connection = ClickHouseConnection.from_config()
    for entity_type in entities_to_process:
        manager = _stats_manager(connection, entity_type, full=job == 'full_refresh')
        try:
            manager.connect()
            message_count = 0
            for message in run(manager):
                yield message
                message_count += 1
            logger.info("%s job for %s yielded %d messages", job, entity_type, message_count)
        except Exception as e:
            logger.error("Error in %s job for %s: %s", job, entity_type, e, exc_info=True)
            yield {'type': 'clk_stats_error', 'entity': entity_type, 'job': job, 'error': str(e)}
        finally:
            if manager.ch_client is not None:
                manager.ch_client.close()

    yield {'type': 'clk_stats_complete', 'job': job, 'entities': entities_to_process}


def run_hourly_stats_job(
    entity: Optional[str] = None,
    batch_size: int = 1000,
) -> Iterator[dict]:
    """Incrementally refresh the stats of ``entity``, or of every stat type."""
    return _run_stats_job('hourly', entity, lambda manager: manager.run_hourly_job(batch_size=batch_size))


def run_full_stats_refresh(
    entity: Optional[str] = None,
    message_batch_size: int = 100,
    user_flush_size: int = 5000,
) -> Iterator[dict]:
    """Recompute the stats of ``entity``, or of every stat type, into new databases.

    ``message_batch_size`` users go in a message; ``user_flush_size`` users are buffered
    from ClickHouse before their messages are sent and their cache state updated.
    """
    return _run_stats_job('full_refresh', entity, lambda manager: manager.run_full_refresh(
        message_batch_size=message_batch_size,
        user_flush_size=user_flush_size,
    ))
