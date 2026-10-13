#!/usr/bin/env python3
"""
ClickHouse Stats Query Handlers

Query handlers for ClickHouse-based incremental stats operations.
These handlers are invoked by the ClickHouse request consumer via RabbitMQ.
"""

import logging
from contextlib import closing
from datetime import datetime
from typing import Callable, Iterator, Optional

from clickhouse import config
from clickhouse.client import ClickHouseConnection
from clickhouse.stats.activity_cache_manager import (
    ACTIVITY_STAT_TYPES,
    ActivityStatsCacheManager,
    BulkActivityStatsCacheManager,
)
from clickhouse.stats.cache_manager import StatsCacheManager, get_cache_config
from clickhouse.stats.deleted_listens import import_deleted_listens as _import_deleted_listens
from clickhouse.stats.ftp import DumpType
from clickhouse.stats.imported_dumps import record_imported_dump
from clickhouse.stats.load_dump import describe_load_errors, import_missing_incremental_dumps, load_dump, load_from_ftp
from clickhouse.stats.schema import ensure_stats_schema

logger = logging.getLogger(__name__)

# Every user stat type the ClickHouse pipeline computes.
STAT_TYPES = ACTIVITY_STAT_TYPES


def _stats_manager(cache_config, stat_type: str, *, full: bool = False):
    manager_class = BulkActivityStatsCacheManager if full else ActivityStatsCacheManager
    return manager_class(cache_config, stat_type)


def _client():
    return closing(ClickHouseConnection.from_config().connect())


def _error(message_type: str, error: Exception, **fields) -> list[dict]:
    """Log a failed request and return the error result message for it."""
    logger.error("%s failed: %s", message_type, error, exc_info=True)
    return [{'type': message_type, 'status': 'error', 'error': str(error), **fields}]


def _raise_on_load_errors(result: dict) -> None:
    if result['errors']:
        raise RuntimeError(describe_load_errors(result['errors']))


def _dump_imported(dump_type: str, result: dict, replace: bool, **fields) -> dict:
    return {
        'type': 'clk_dump_imported',
        'dump_type': dump_type,
        'status': 'success',
        'dump_id': result.get('dump_id'),
        'load_id': result['load_id'],
        'replace': replace,
        'total_inserted': result['total_inserted'],
        'files_completed': result['files_completed'],
        **fields,
    }


def _load_dump_from_path(dump_path: str, dump_type: str, workers: int = 4, replace: bool = False) -> list[dict]:
    """Load a directory of Parquet files into the ClickHouse listens table."""
    try:
        result = load_dump(dump_path, ClickHouseConnection.from_config(), workers=workers, replace=replace)
        _raise_on_load_errors(result)
    except Exception as e:
        return _error('clk_dump_imported', e, dump_type=dump_type)
    return [_dump_imported(dump_type, result, replace, dump_path=dump_path)]


def load_full_dump(dump_path: str, workers: int = 4, replace: bool = True) -> list[dict]:
    """Load a full Parquet dump into ClickHouse listens table.

    By default replaces the existing listens / stats (full dump semantics); pass
    replace=False to merge into the existing data instead (already present
    listens are skipped).
    """
    return _load_dump_from_path(dump_path, "full", workers, replace=replace)


def load_incremental_dump(dump_path: str, workers: int = 4) -> list[dict]:
    """Load an incremental Parquet dump directory into ClickHouse listens table."""
    return _load_dump_from_path(dump_path, "incremental", workers)


def init_schema() -> list[dict]:
    """Create the ClickHouse stats schema."""
    try:
        with _client() as ch_client:
            ensure_stats_schema(ch_client)
    except Exception as e:
        return _error('clk_schema_initialized', e)
    return [{'type': 'clk_schema_initialized', 'status': 'success'}]


def import_full_dump(workers: int = 4, replace: bool = True) -> list[dict]:
    """Download latest full listens dump from FTP and load into ClickHouse.

    By default replaces the existing listens / stats (full dump semantics).
    """
    try:
        result = load_from_ftp(DumpType.FULL, ClickHouseConnection.from_config(), workers=workers, replace=replace)
        _raise_on_load_errors(result)
    except Exception as e:
        return _error('clk_dump_imported', e, dump_type='full')
    return [_dump_imported('full', result, replace)]


def import_incremental_dump(workers: int = 4, max_dumps: Optional[int] = None) -> list[dict]:
    """
    Import every incremental dump on FTP that ClickHouse has not loaded yet.

    Dumps are loaded oldest first and stop at the first failure, so a dump that could
    not be loaded is retried by the next run instead of being skipped over.

    Args:
        workers: Number of parallel workers for loading
        max_dumps: Load at most this many dumps in this run; None loads the whole backlog.

    Returns:
        List of result messages for the response queue, one per dump loaded plus one
        for the failure that stopped the run, if any.
    """
    try:
        result = import_missing_incremental_dumps(
            ClickHouseConnection.from_config(), workers=workers, max_dumps=max_dumps,
        )
    except Exception as e:
        return _error('clk_dump_imported', e, dump_type='incremental')

    pending = result['pending']
    messages = [_dump_imported('incremental', dump, False, pending=pending) for dump in result['imported']]
    messages.extend({
        'type': 'clk_dump_imported', 'dump_type': 'incremental', 'status': 'error',
        'dump_id': dump_id, 'pending': pending, 'error': error,
    } for dump_id, error in result['errors'])

    if not messages:
        logger.info("No incremental dumps to import")
    return messages


def record_dump_import(dump_id: int, dump_type: str, imported_at: Optional[str] = None) -> list[dict]:
    """
    Record a dump as already loaded, without loading it.

    For dumps that went into listens before ``imported_dumps`` existed, so the
    incremental catch-up knows where to resume instead of treating the whole FTP
    listing as missing.

    Args:
        dump_id: Id of the dump that is already in listens.
        dump_type: 'full' or 'incremental'.
        imported_at: When it was loaded, as a UTC 'YYYY-MM-DD HH:MM:SS[.mmm]' string;
            defaults to now. A dump loaded before the latest full dump import must
            carry its real timestamp, otherwise the catch-up reads it as newer than
            that full dump and skips dumps it should load.

    Returns:
        List of result messages for the response queue
    """
    try:
        parsed_type = DumpType(dump_type)
    except ValueError:
        error = ValueError(f"Unknown dump type {dump_type!r}, expected one of {[t.value for t in DumpType]}")
        return _error('clk_dump_import_recorded', error, dump_id=dump_id)

    try:
        parsed_at = datetime.fromisoformat(imported_at) if imported_at else None
        with _client() as ch_client:
            ensure_stats_schema(ch_client)
            record_imported_dump(ch_client, dump_id, parsed_type, parsed_at)
    except Exception as e:
        return _error('clk_dump_import_recorded', e, dump_id=dump_id)

    return [{
        'type': 'clk_dump_import_recorded', 'status': 'success',
        'dump_id': dump_id, 'dump_type': parsed_type.value, 'imported_at': imported_at,
    }]


def import_deleted_listens(batch_size: int = 10_000) -> list[dict]:
    """
    Import listen deletions from the ListenBrainz listens database and apply them
    to ClickHouse listens.

    Args:
        batch_size: Number of rows to fetch from the listens database per batch.

    Returns:
        List of result messages for the response queue
    """
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
    """Run ``run`` on the manager of ``entity`` (or of every stat type) and yield its messages.

    A failing stat type is reported with a clk_stats_error message and does not stop the
    others; a clk_stats_complete message closes the job.
    """
    if entity and entity not in STAT_TYPES:
        yield {'type': 'clk_stats_error', 'entity': entity, 'job': job, 'error': f"Unknown entity: {entity}"}
        return
    entities_to_process = [entity] if entity else list(STAT_TYPES)
    logger.info("Running %s stats job for entities: %s", job, entities_to_process)

    cache_config = get_cache_config()
    for entity_type in entities_to_process:
        manager = _stats_manager(cache_config, entity_type, full=job == 'full_refresh')
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
    """
    Run the hourly stats cache refresh job from an RMQ request.

    Args:
        entity: Stat type to process, or None for all ClickHouse user stats.
        batch_size: Number of users to process per batch

    Yields:
        Result messages for the response queue.
    """
    return _run_stats_job('hourly', entity, lambda manager: manager.run_hourly_job(batch_size=batch_size))


def run_full_stats_refresh(
    entity: Optional[str] = None,
    message_batch_size: int = 100,
    user_flush_size: int = 5000,
) -> Iterator[dict]:
    """
    Run a full stats cache refresh from an RMQ request.

    Builds a compact intermediate per stat type, then streams each time range
    from it, aggregating weekday/hour or timeline buckets. Emits start / data /
    end messages so the LB CouchDB handler swaps databases per (stat type, time
    range).

    Args:
        entity: Stat type to process, or None for all ClickHouse user stats.
        message_batch_size: Users per outbound RMQ message.
        user_flush_size: Users buffered from the ClickHouse stream before
            messages are emitted and cache state is updated.

    Yields:
        Result messages for the response queue.
    """
    return _run_stats_job('full_refresh', entity, lambda manager: manager.run_full_refresh(
        message_batch_size=message_batch_size,
        user_flush_size=user_flush_size,
    ))
