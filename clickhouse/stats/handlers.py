#!/usr/bin/env python3
"""
ClickHouse Stats Query Handlers

Query handlers for ClickHouse-based incremental stats operations.
These handlers are invoked by the ClickHouse request consumer via RabbitMQ.
"""

import logging
from typing import Iterator, Optional

from clickhouse import config
from clickhouse.stats.bulk_cache_manager import BulkStatsCacheManager
from clickhouse.stats.cache_manager import (
    StatsCacheManager,
    ENTITY_CONFIGS,
    get_cache_config,
)
from clickhouse.stats.ftp import DumpType
from clickhouse.stats.load_dump import load_dump, load_from_ftp
from clickhouse.stats.refresh_metadata_cache import refresh_metadata_caches, PG_QUERIES

logger = logging.getLogger(__name__)


def _raise_on_dump_errors(result: dict) -> None:
    errors = result.get('errors') or []
    if errors:
        examples = "; ".join(f"{path}: {error}" for path, error in errors[:3])
        raise RuntimeError(f"{len(errors)} parquet file(s) failed to load: {examples}")


def _load_dump_from_path(dump_path: str, dump_type: str, workers: int = 4) -> list[dict]:
    """
    Load a Parquet dump into ClickHouse listens table.

    Args:
        dump_path: Path to directory containing Parquet files
        dump_type: Dump type label to report in the result message.
        workers: Number of parallel workers for loading

    Returns:
        List of result messages for the response queue
    """
    try:
        result = load_dump(
            directory=dump_path,
            workers=workers,
            **_ch_kwargs(),
        )
        _raise_on_dump_errors(result)
        return [{
            'type': 'clk_dump_imported',
            'dump_type': dump_type,
            'status': 'success',
            'dump_path': dump_path,
            'dump_id': None,
            'total_inserted': result['total_inserted'],
            'files_completed': result['files_completed'],
        }]
    except Exception as e:
        logger.error("Error loading %s dump: %s", dump_type, str(e), exc_info=True)
        return [{'type': 'clk_dump_imported', 'dump_type': dump_type, 'status': 'error', 'error': str(e)}]


def load_full_dump(dump_path: str, workers: int = 4) -> list[dict]:
    """Load a full Parquet dump into ClickHouse listens table."""
    return _load_dump_from_path(dump_path, "full", workers)


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


def import_full_dump(workers: int = 4) -> list[dict]:
    """Download latest full listens dump from FTP and load into ClickHouse."""
    try:
        result = load_from_ftp(dump_type=DumpType.FULL, workers=workers, **_ch_kwargs())
        _raise_on_dump_errors(result)
        return [{'type': 'clk_dump_imported', 'dump_type': 'full', 'status': 'success',
                 'dump_id': result['dump_id'], 'total_inserted': result['total_inserted'],
                 'files_completed': result['files_completed']}]
    except Exception as e:
        logger.error("Error importing full dump: %s", str(e), exc_info=True)
        return [{'type': 'clk_dump_imported', 'dump_type': 'full', 'status': 'error', 'error': str(e)}]


def import_incremental_dump(workers: int = 4) -> list[dict]:
    """
    Download latest incremental dump from FTP and import into ClickHouse.

    Args:
        workers: Number of parallel workers for loading

    Returns:
        List of result messages for the response queue
    """
    try:
        result = load_from_ftp(dump_type=DumpType.INCREMENTAL, workers=workers, **_ch_kwargs())
        _raise_on_dump_errors(result)
        return [{'type': 'clk_dump_imported', 'dump_type': 'incremental', 'status': 'success',
                 'dump_id': result['dump_id'], 'total_inserted': result['total_inserted'],
                 'files_completed': result['files_completed']}]
    except Exception as e:
        logger.error("Error importing incremental dump: %s", str(e), exc_info=True)
        return [{'type': 'clk_dump_imported', 'dump_type': 'incremental', 'status': 'error', 'error': str(e)}]


def run_hourly_stats_job(
    entity: Optional[str] = None,
    batch_size: int = 1000,
) -> Iterator[dict]:
    """
    Run the hourly stats cache refresh job from an RMQ request.

    Args:
        entity: Entity type to process ('artists', 'recordings', 'release_groups', or None for all)
        batch_size: Number of users to process per batch

    Yields:
        Result messages for the response queue.
    """
    cache_config = get_cache_config()

    if entity:
        if entity not in ENTITY_CONFIGS:
            yield {
                'type': 'clk_stats_error',
                'entity': entity,
                'job': 'hourly',
                'error': f"Unknown entity: {entity}",
            }
            return
        entities_to_process = [entity]
    else:
        entities_to_process = list(ENTITY_CONFIGS)

    logger.info("Running hourly stats job for entities: %s", entities_to_process)

    for entity_type in entities_to_process:
        try:
            entity_config = ENTITY_CONFIGS[entity_type]
            manager = StatsCacheManager(cache_config, entity_config)
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
    batch_size: int = 1000,
) -> Iterator[dict]:
    """
    Run a full stats cache refresh from an RMQ request.

    Args:
        entity: Entity type to process ('artists', 'recordings', 'release_groups', or None for all)
        batch_size: Number of users to process per batch

    Yields:
        Result messages for the response queue.
    """
    cache_config = get_cache_config()

    if entity:
        if entity not in ENTITY_CONFIGS:
            yield {
                'type': 'clk_stats_error',
                'entity': entity,
                'job': 'full_refresh',
                'error': f"Unknown entity: {entity}",
            }
            return
        entities_to_process = [entity]
    else:
        entities_to_process = list(ENTITY_CONFIGS)

    logger.info("Running full stats refresh for entities: %s", entities_to_process)

    for entity_type in entities_to_process:
        try:
            entity_config = ENTITY_CONFIGS[entity_type]
            manager = StatsCacheManager(cache_config, entity_config)
            manager.connect()

            message_count = 0
            for message in manager.run_full_refresh(batch_size=batch_size):
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


def run_bulk_full_stats_refresh(
    entity: Optional[str] = None,
    message_batch_size: int = 100,
    user_flush_size: int = 5000,
) -> Iterator[dict]:
    """
    Run a bulk full stats refresh from an RMQ request.

    Uses BulkStatsCacheManager: builds a single per-entity intermediate from
    user_*_stats_daily (one scan covering all time ranges via conditional
    aggregation), then streams a top-N ranking per time range off that
    intermediate. Emits the same start / data / end message contract as
    run_full_stats_refresh so the LB CouchDB handler swaps databases per
    (entity, time_range).

    Args:
        entity: Entity type to process ('artists', 'recordings', 'release_groups',
            or None for all).
        message_batch_size: Users per outbound RMQ message.
        user_flush_size: Users buffered from the ClickHouse stream before
            messages are emitted and cache state is updated.

    Yields:
        Result messages for the response queue.
    """
    cache_config = get_cache_config()

    if entity:
        if entity not in ENTITY_CONFIGS:
            yield {
                'type': 'clk_stats_error',
                'entity': entity,
                'job': 'bulk_full_refresh',
                'error': f"Unknown entity: {entity}",
            }
            return
        entities_to_process = [entity]
    else:
        entities_to_process = list(ENTITY_CONFIGS)

    logger.info("Running bulk full stats refresh for entities: %s", entities_to_process)

    for entity_type in entities_to_process:
        try:
            entity_config = ENTITY_CONFIGS[entity_type]
            manager = BulkStatsCacheManager(cache_config, entity_config)
            manager.connect()

            message_count = 0
            for message in manager.run_bulk_full_refresh(
                message_batch_size=message_batch_size,
                user_flush_size=user_flush_size,
            ):
                yield message
                message_count += 1

            logger.info("Bulk refresh for %s yielded %d messages", entity_type, message_count)
        except Exception as e:
            logger.error("Error in bulk full refresh for %s: %s", entity_type, e, exc_info=True)
            yield {
                'type': 'clk_stats_error',
                'entity': entity_type,
                'job': 'bulk_full_refresh',
                'error': str(e),
            }

    yield {
        'type': 'clk_stats_complete',
        'job': 'bulk_full_refresh',
        'entities': entities_to_process,
    }


def refresh_metadata_cache(
    cache_types: Optional[list[str]] = None,
    batch_size: int = 100_000,
    max_retries: int = 2,
) -> list[dict]:
    """
    Refresh ClickHouse metadata tables directly from MusicBrainz PostgreSQL.

    Args:
        cache_types: List of cache types to refresh ('artist', 'recording', 'release',
                     'release_group'), or None to refresh all.
        batch_size: Number of rows to fetch from PostgreSQL per batch.
        max_retries: Number of times to retry a cache after a recoverable PostgreSQL
                     connection failure.

    Returns:
        List of result messages for the response queue.
    """
    try:
        pg_dsn = config.MUSICBRAINZ_PG_DSN

        import clickhouse_connect
        ch_client = clickhouse_connect.get_client(
            host=config.CLICKHOUSE_HOST,
            port=config.CLICKHOUSE_PORT,
            username=config.CLICKHOUSE_USERNAME,
            password=config.CLICKHOUSE_PASSWORD,
            database=config.CLICKHOUSE_DATABASE,
            compress=False,
            form_encode_query_params=True,
        )

        valid_types = list(PG_QUERIES.keys())
        if cache_types:
            invalid = [t for t in cache_types if t not in valid_types]
            if invalid:
                raise ValueError(f"Unknown cache type(s): {invalid}. Valid: {valid_types}")

        results = refresh_metadata_caches(pg_dsn, ch_client, cache_types, batch_size, max_retries)
        ch_client.close()

        errors = {t: rows for t, rows in results.items() if rows < 0}
        if errors:
            return [{
                'type': 'clk_metadata_cache_refresh',
                'status': 'error',
                'results': results,
                'errors': list(errors.keys()),
            }]

        return [{
            'type': 'clk_metadata_cache_refresh',
            'status': 'success',
            'results': results,
        }]

    except Exception as e:
        logger.error("Error refreshing metadata cache: %s", str(e), exc_info=True)
        return [{
            'type': 'clk_metadata_cache_refresh',
            'status': 'error',
            'error': str(e),
        }]
