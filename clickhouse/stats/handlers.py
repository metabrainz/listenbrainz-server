#!/usr/bin/env python3
"""
ClickHouse Stats Query Handlers

Query handlers for ClickHouse-based incremental stats operations.
These handlers are invoked by the ClickHouse request consumer via RabbitMQ.
"""

import logging
from typing import Iterator, Optional

from kombu import Exchange, Queue

from clickhouse.stats.cache_manager import (
    CacheConfig,
    StatsCacheManager,
    ENTITY_CONFIGS,
    get_cache_config_from_config,
)
from clickhouse.stats.ftp import DumpType
from clickhouse.stats.load_dump import load_dump, load_from_ftp, load_from_local
from clickhouse.stats.refresh_metadata_cache import refresh_metadata_caches, PG_QUERIES

logger = logging.getLogger(__name__)


# ClickHouse request exchange and queue
# Used by LB to send stats/dump requests to the ClickHouse service
CLICKHOUSE_EXCHANGE = Exchange("clickhouse", "direct", durable=True)
CLICKHOUSE_QUEUE = Queue("clickhouse", exchange=CLICKHOUSE_EXCHANGE, routing_key="clickhouse", durable=True)

# ClickHouse result exchange and queue
# Used by ClickHouse service to send results (stats data, notifications) back to LB
CLICKHOUSE_RESULT_EXCHANGE = Exchange("clickhouse_result", "direct", durable=True)
CLICKHOUSE_RESULT_QUEUE = Queue("clickhouse_result", exchange=CLICKHOUSE_RESULT_EXCHANGE, routing_key="clickhouse_result", durable=True)


def _get_cache_config() -> CacheConfig:
    """Get CacheConfig from the clickhouse config module."""
    try:
        from clickhouse import config
        return get_cache_config_from_config(config)
    except ImportError:
        logger.warning("clickhouse.config not found, using defaults")
        return CacheConfig()


def load_full_dump(dump_path: str, workers: int = 4) -> list[dict]:
    """
    Load a full Parquet dump into ClickHouse listens table.

    Args:
        dump_path: Path to directory containing Parquet files
        workers: Number of parallel workers for loading

    Returns:
        List of result messages for the response queue
    """
    try:
        from clickhouse import config
        result = load_dump(
            directory=dump_path,
            host=getattr(config, 'CLICKHOUSE_HOST', 'localhost'),
            port=getattr(config, 'CLICKHOUSE_PORT', 8123),
            username=getattr(config, 'CLICKHOUSE_USERNAME', 'default'),
            password=getattr(config, 'CLICKHOUSE_PASSWORD', ''),
            database=getattr(config, 'CLICKHOUSE_DATABASE', 'default'),
            workers=workers,
        )
        return [{
            'type': 'clickhouse_load_full_dump',
            'status': 'success',
            'dump_path': dump_path,
            'total_inserted': result['total_inserted'],
            'files_completed': result['files_completed'],
        }]
    except Exception as e:
        logger.error("Error loading full dump: %s", str(e), exc_info=True)
        return [{'type': 'clickhouse_load_full_dump', 'status': 'error', 'error': str(e)}]


def load_incremental_dump(dump_path: str, workers: int = 4) -> list[dict]:
    """Load an incremental Parquet dump directory into ClickHouse listens table."""
    return load_full_dump(dump_path, workers)


def _ch_kwargs() -> dict:
    """Return ClickHouse connection kwargs from config."""
    from clickhouse import config
    return {
        'host': getattr(config, 'CLICKHOUSE_HOST', 'localhost'),
        'port': getattr(config, 'CLICKHOUSE_PORT', 8123),
        'username': getattr(config, 'CLICKHOUSE_USERNAME', 'default'),
        'password': getattr(config, 'CLICKHOUSE_PASSWORD', ''),
        'database': getattr(config, 'CLICKHOUSE_DATABASE', 'default'),
    }


def import_full_dump(workers: int = 4) -> list[dict]:
    """Download latest full listens dump from FTP and load into ClickHouse."""
    try:
        result = load_from_ftp(dump_type=DumpType.FULL, workers=workers, **_ch_kwargs())
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
    Run the hourly stats cache refresh job.

    Stats are computed in ClickHouse and messages are yielded to be sent via RMQ.
    The LB-side handler will insert the stats into CouchDB.

    Args:
        entity: Entity type to process ('artist', 'recording', 'release_group', or None for all)
        batch_size: Number of users to process per batch

    Yields:
        Result messages for the response queue (stats data to insert into CouchDB)
    """
    cache_config = _get_cache_config()

    if entity and entity in ENTITY_CONFIGS:
        entities_to_process = [entity]
    else:
        entities_to_process = ['artist', 'recording', 'release_group']

    logger.info(f"Running hourly stats job for entities: {entities_to_process}")

    for entity_type in entities_to_process:
        try:
            entity_config = ENTITY_CONFIGS[entity_type]
            manager = StatsCacheManager(cache_config, entity_config)
            manager.connect()

            # Use RMQ mode - yield messages as they're generated
            message_count = 0
            for message in manager.run_hourly_job_for_rmq(batch_size=batch_size):
                yield message
                message_count += 1

            logger.info(f"Hourly job for {entity_type} yielded {message_count} messages")
        except Exception as e:
            logger.error(f"Error in hourly job for {entity_type}: {e}", exc_info=True)
            yield {
                'type': 'clk_stats_error',
                'entity': entity_type,
                'job': 'hourly',
                'error': str(e),
            }

    # Yield completion message
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
    Run a full stats cache refresh for all users.

    Stats are computed in ClickHouse and messages are yielded to be sent via RMQ.
    The LB-side handler will insert the stats into CouchDB.

    Args:
        entity: Entity type to process ('artist', 'recording', 'release_group', or None for all)
        batch_size: Number of users to process per batch

    Yields:
        Result messages for the response queue (stats data to insert into CouchDB)
    """
    cache_config = _get_cache_config()

    if entity and entity in ENTITY_CONFIGS:
        entities_to_process = [entity]
    else:
        entities_to_process = ['artist', 'recording', 'release_group']

    logger.info(f"Running full stats refresh for entities: {entities_to_process}")

    for entity_type in entities_to_process:
        try:
            entity_config = ENTITY_CONFIGS[entity_type]
            manager = StatsCacheManager(cache_config, entity_config)
            manager.connect()

            # Use RMQ mode - yield messages as they're generated
            message_count = 0
            for message in manager.run_full_refresh_for_rmq(batch_size=batch_size):
                yield message
                message_count += 1

            logger.info(f"Full refresh for {entity_type} yielded {message_count} messages")
        except Exception as e:
            logger.error(f"Error in full refresh for {entity_type}: {e}", exc_info=True)
            yield {
                'type': 'clk_stats_error',
                'entity': entity_type,
                'job': 'full_refresh',
                'error': str(e),
            }

    # Yield completion message
    yield {
        'type': 'clk_stats_complete',
        'job': 'full_refresh',
        'entities': entities_to_process,
    }


def refresh_metadata_cache(
    cache_types: Optional[list[str]] = None,
    batch_size: int = 100_000,
) -> list[dict]:
    """
    Refresh ClickHouse metadata tables directly from MusicBrainz PostgreSQL.

    Args:
        cache_types: List of cache types to refresh ('artist', 'recording', 'release',
                     'release_group'), or None to refresh all.
        batch_size: Number of rows to fetch from PostgreSQL per batch.

    Returns:
        List of result messages for the response queue.
    """
    try:
        from clickhouse import config
        pg_dsn = getattr(config, 'MUSICBRAINZ_PG_DSN', None)
        if not pg_dsn:
            raise ValueError("MUSICBRAINZ_PG_DSN is not configured")

        import clickhouse_connect
        ch_client = clickhouse_connect.get_client(
            host=getattr(config, 'CLICKHOUSE_HOST', 'localhost'),
            port=getattr(config, 'CLICKHOUSE_PORT', 8123),
            username=getattr(config, 'CLICKHOUSE_USERNAME', 'default'),
            password=getattr(config, 'CLICKHOUSE_PASSWORD', ''),
            database=getattr(config, 'CLICKHOUSE_DATABASE', 'default'),
            compress=False,
        )

        valid_types = list(PG_QUERIES.keys())
        if cache_types:
            invalid = [t for t in cache_types if t not in valid_types]
            if invalid:
                raise ValueError(f"Unknown cache type(s): {invalid}. Valid: {valid_types}")

        results = refresh_metadata_caches(pg_dsn, ch_client, cache_types, batch_size)
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
