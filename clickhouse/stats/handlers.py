#!/usr/bin/env python3
"""
ClickHouse Stats Query Handlers

Query handlers for ClickHouse-based incremental stats operations.
These handlers are invoked by the ClickHouse request consumer via RabbitMQ.
"""

import logging
from datetime import datetime
from typing import Iterator, Optional

from clickhouse import config
from clickhouse.stats.activity_cache_manager import (
    ACTIVITY_STAT_TYPES,
    ActivityStatsCacheManager,
    BulkActivityStatsCacheManager,
)
from clickhouse.stats.deleted_listens import import_deleted_listens as _import_deleted_listens
from clickhouse.stats.cache_manager import get_cache_config
from clickhouse.stats.ftp import DumpType
from clickhouse.stats.imported_dumps import record_imported_dump
from clickhouse.stats.load_dump import import_missing_incremental_dumps, load_dump, load_from_ftp
from clickhouse.stats.schema import ensure_stats_schema

logger = logging.getLogger(__name__)

# Every user stat type the ClickHouse pipeline computes.
STAT_TYPES = ACTIVITY_STAT_TYPES


def _stats_manager(cache_config, stat_type: str, *, full: bool = False):
    manager_class = BulkActivityStatsCacheManager if full else ActivityStatsCacheManager
    return manager_class(cache_config, stat_type)


def _raise_on_dump_errors(result: dict) -> None:
    errors = result.get('errors') or []
    if errors:
        examples = "; ".join(f"{path}: {error}" for path, error in errors[:3])
        raise RuntimeError(f"{len(errors)} parquet file(s) failed to load: {examples}")


def _load_dump_from_path(dump_path: str, dump_type: str, workers: int = 4, replace: bool = False) -> list[dict]:
    """
    Load a Parquet dump into ClickHouse listens table.

    Args:
        dump_path: Path to directory containing Parquet files
        dump_type: Dump type label to report in the result message.
        workers: Number of parallel workers for loading
        replace: Truncate listens and cache state before loading.

    Returns:
        List of result messages for the response queue
    """
    try:
        result = load_dump(
            directory=dump_path,
            workers=workers,
            replace=replace,
            **_ch_kwargs(),
        )
        _raise_on_dump_errors(result)
        return [{
            'type': 'clk_dump_imported',
            'dump_type': dump_type,
            'status': 'success',
            'dump_path': dump_path,
            'dump_id': None,
            'load_id': result['load_id'],
            'replace': replace,
            'total_inserted': result['total_inserted'],
            'files_completed': result['files_completed'],
        }]
    except Exception as e:
        logger.error("Error loading %s dump: %s", dump_type, str(e), exc_info=True)
        return [{'type': 'clk_dump_imported', 'dump_type': dump_type, 'status': 'error', 'error': str(e)}]


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


def _ch_kwargs() -> dict:
    """Return ClickHouse connection kwargs from config."""
    return {
        'host': config.CLICKHOUSE_HOST,
        'port': config.CLICKHOUSE_PORT,
        'username': config.CLICKHOUSE_USERNAME,
        'password': config.CLICKHOUSE_PASSWORD,
        'database': config.CLICKHOUSE_DATABASE,
    }


def init_schema() -> list[dict]:
    """
    Create the ClickHouse stats schema.

    Returns:
        List of result messages for the response queue
    """
    try:
        import clickhouse_connect
        ch_client = clickhouse_connect.get_client(**_ch_kwargs())
        try:
            ensure_stats_schema(ch_client)
        finally:
            ch_client.close()
        return [{'type': 'clk_schema_initialized', 'status': 'success'}]
    except Exception as e:
        logger.error("Error initializing ClickHouse schema: %s", str(e), exc_info=True)
        return [{'type': 'clk_schema_initialized', 'status': 'error', 'error': str(e)}]


def import_full_dump(workers: int = 4, replace: bool = True) -> list[dict]:
    """Download latest full listens dump from FTP and load into ClickHouse.

    By default replaces the existing listens / stats (full dump semantics).
    """
    try:
        result = load_from_ftp(dump_type=DumpType.FULL, workers=workers, replace=replace, **_ch_kwargs())
        _raise_on_dump_errors(result)
        return [{'type': 'clk_dump_imported', 'dump_type': 'full', 'status': 'success',
                 'dump_id': result['dump_id'], 'load_id': result['load_id'], 'replace': replace,
                 'total_inserted': result['total_inserted'],
                 'files_completed': result['files_completed']}]
    except Exception as e:
        logger.error("Error importing full dump: %s", str(e), exc_info=True)
        return [{'type': 'clk_dump_imported', 'dump_type': 'full', 'status': 'error', 'error': str(e)}]


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
        result = import_missing_incremental_dumps(workers=workers, max_dumps=max_dumps, **_ch_kwargs())
    except Exception as e:
        logger.error("Error importing incremental dumps: %s", str(e), exc_info=True)
        return [{'type': 'clk_dump_imported', 'dump_type': 'incremental', 'status': 'error', 'error': str(e)}]

    messages = [{
        'type': 'clk_dump_imported', 'dump_type': 'incremental', 'status': 'success',
        'dump_id': dump['dump_id'], 'load_id': dump['load_id'], 'replace': False,
        'total_inserted': dump['total_inserted'],
        'files_completed': dump['files_completed'],
        'pending': result['pending'],
    } for dump in result['imported']]

    messages.extend({
        'type': 'clk_dump_imported', 'dump_type': 'incremental', 'status': 'error',
        'dump_id': dump_id, 'pending': result['pending'], 'error': error,
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
        error = f"Unknown dump type {dump_type!r}, expected one of {[t.value for t in DumpType]}"
        logger.error(error)
        return [{'type': 'clk_dump_import_recorded', 'status': 'error', 'dump_id': dump_id, 'error': error}]

    try:
        parsed_at = None
        if imported_at:
            parsed_at = datetime.fromisoformat(imported_at)

        import clickhouse_connect
        ch_client = clickhouse_connect.get_client(**_ch_kwargs())
        try:
            ensure_stats_schema(ch_client)
            record_imported_dump(ch_client, dump_id, parsed_type, parsed_at)
        finally:
            ch_client.close()
    except Exception as e:
        logger.error("Error recording dump %s as imported: %s", dump_id, str(e), exc_info=True)
        return [{'type': 'clk_dump_import_recorded', 'status': 'error', 'dump_id': dump_id, 'error': str(e)}]

    return [{
        'type': 'clk_dump_import_recorded', 'status': 'success',
        'dump_id': dump_id, 'dump_type': parsed_type.value, 'imported_at': imported_at,
    }]


def import_deleted_listens(batch_size: int = 10_000) -> list[dict]:
    """
    Import listen deletions from the ListenBrainz timescale database and apply them
    to ClickHouse listens.

    Args:
        batch_size: Number of rows to fetch from timescale per batch.

    Returns:
        List of result messages for the response queue
    """
    try:
        ts_dsn = config.TIMESCALE_DSN
        if not ts_dsn:
            raise ValueError("TIMESCALE_DSN is not configured")

        import clickhouse_connect
        ch_client = clickhouse_connect.get_client(**_ch_kwargs())
        try:
            summary = _import_deleted_listens(ts_dsn, ch_client, batch_size=batch_size)
        finally:
            ch_client.close()
        return [{'type': 'clk_deleted_listens_imported', 'status': 'success', **summary}]
    except Exception as e:
        logger.error("Error importing deleted listens: %s", str(e), exc_info=True)
        return [{'type': 'clk_deleted_listens_imported', 'status': 'error', 'error': str(e)}]


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
    cache_config = get_cache_config()

    if entity:
        if entity not in STAT_TYPES:
            yield {
                'type': 'clk_stats_error',
                'entity': entity,
                'job': 'hourly',
                'error': f"Unknown entity: {entity}",
            }
            return
        entities_to_process = [entity]
    else:
        entities_to_process = list(STAT_TYPES)

    logger.info("Running hourly stats job for entities: %s", entities_to_process)

    for entity_type in entities_to_process:
        try:
            manager = _stats_manager(cache_config, entity_type)
            manager.connect()

            message_count = 0
            for message in manager.run_hourly_job(batch_size=batch_size):
                yield message
                message_count += 1

            logger.info("Hourly job for %s yielded %d messages", entity_type, message_count)
        except Exception as e:
            logger.error("Error in hourly job for %s: %s", entity_type, e, exc_info=True)
            yield {
                'type': 'clk_stats_error',
                'entity': entity_type,
                'job': 'hourly',
                'error': str(e),
            }

    yield {
        'type': 'clk_stats_complete',
        'job': 'hourly',
        'entities': entities_to_process,
    }


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
    cache_config = get_cache_config()

    if entity:
        if entity not in STAT_TYPES:
            yield {
                'type': 'clk_stats_error',
                'entity': entity,
                'job': 'full_refresh',
                'error': f"Unknown entity: {entity}",
            }
            return
        entities_to_process = [entity]
    else:
        entities_to_process = list(STAT_TYPES)

    logger.info("Running full stats refresh for entities: %s", entities_to_process)

    for entity_type in entities_to_process:
        try:
            manager = _stats_manager(cache_config, entity_type, full=True)
            manager.connect()

            message_count = 0
            for message in manager.run_full_refresh(
                message_batch_size=message_batch_size,
                user_flush_size=user_flush_size,
            ):
                yield message
                message_count += 1

            logger.info("Full refresh for %s yielded %d messages", entity_type, message_count)
        except Exception as e:
            logger.error("Error in full refresh for %s: %s", entity_type, e, exc_info=True)
            yield {
                'type': 'clk_stats_error',
                'entity': entity_type,
                'job': 'full_refresh',
                'error': str(e),
            }

    yield {
        'type': 'clk_stats_complete',
        'job': 'full_refresh',
        'entities': entities_to_process,
    }
