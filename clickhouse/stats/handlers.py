#!/usr/bin/env python3
"""
ClickHouse Stats Query Handlers

Query handlers for ClickHouse-based incremental stats operations.
These handlers are invoked by the ClickHouse request consumer via RabbitMQ.
"""

import logging
import os
import shutil
import subprocess
import tempfile
from typing import Iterator, Optional

from kombu import Exchange, Queue

from clickhouse.stats.cache_manager import (
    CacheConfig,
    StatsCacheManager,
    ENTITY_CONFIGS,
    get_cache_config_from_config,
)
from clickhouse.stats.ftp import download_dump
from clickhouse.stats.load_dump import load_dump

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
            use_arrow=True,
        )

        return [{
            'type': 'clickhouse_load_full_dump',
            'status': 'success',
            'dump_path': dump_path,
            'total_inserted': result['total_inserted'],
            'files_completed': result['files_completed'],
        }]
    except Exception as e:
        logger.error(f"Error loading full dump: {e}", exc_info=True)
        return [{
            'type': 'clickhouse_load_full_dump',
            'status': 'error',
            'error': str(e),
        }]


def load_incremental_dump(dump_path: str, workers: int = 4) -> list[dict]:
    """Load an incremental Parquet dump into ClickHouse listens table."""
    return load_full_dump(dump_path, workers)


def _extract_dump(archive_path: str, extract_dir: str) -> str:
    """
    Extract a .tar.zst dump archive.

    Args:
        archive_path: Path to the .tar.zst archive
        extract_dir: Directory to extract to

    Returns:
        Path to the extracted directory containing Parquet files
    """
    logger.info(f"Extracting {archive_path} to {extract_dir}")

    # Use tar with zstd decompression
    subprocess.run(
        ['tar', '--use-compress-program=zstd', '-xf', archive_path, '-C', extract_dir],
        check=True
    )

    # Find the extracted directory (should be the only directory in extract_dir)
    extracted_items = os.listdir(extract_dir)
    for item in extracted_items:
        item_path = os.path.join(extract_dir, item)
        if os.path.isdir(item_path):
            return item_path

    # If no subdirectory, the files are directly in extract_dir
    return extract_dir


def _import_dump(dump_type: str, workers: int = 4) -> list[dict]:
    """
    Download and import a dump from FTP.

    Args:
        dump_type: "full" or "incremental"
        workers: Number of parallel workers for loading

    Returns:
        List of result messages for the response queue
    """
    download_dir = None
    extract_dir = None

    try:
        from clickhouse import config

        # Create temp directories
        download_dir = tempfile.mkdtemp(prefix="clickhouse_download_")
        extract_dir = tempfile.mkdtemp(prefix="clickhouse_extract_")

        # Download dump from FTP
        logger.info(f"Downloading {dump_type} dump from FTP...")
        archive_path, dump_id = download_dump(
            dump_type=dump_type,
            download_dir=download_dir,
            ftp_server=getattr(config, 'FTP_SERVER_URI', None),
            ftp_dir=getattr(config, 'FTP_LISTENS_DIR', None),
        )
        logger.info(f"Downloaded dump {dump_id}: {archive_path}")

        # Extract the archive
        parquet_dir = _extract_dump(archive_path, extract_dir)
        logger.info(f"Extracted to: {parquet_dir}")

        # Load into ClickHouse
        result = load_dump(
            directory=parquet_dir,
            host=getattr(config, 'CLICKHOUSE_HOST', 'localhost'),
            port=getattr(config, 'CLICKHOUSE_PORT', 8123),
            username=getattr(config, 'CLICKHOUSE_USERNAME', 'default'),
            password=getattr(config, 'CLICKHOUSE_PASSWORD', ''),
            database=getattr(config, 'CLICKHOUSE_DATABASE', 'default'),
            workers=workers,
            use_arrow=True,
        )

        return [{
            'type': f'clk_dump_imported',
            'dump_type': dump_type,
            'dump_id': dump_id,
            'status': 'success',
            'total_inserted': result['total_inserted'],
            'files_completed': result['files_completed'],
        }]

    except Exception as e:
        logger.error(f"Error importing {dump_type} dump: {e}", exc_info=True)
        return [{
            'type': f'clk_dump_imported',
            'dump_type': dump_type,
            'status': 'error',
            'error': str(e),
        }]

    finally:
        # Clean up temp directories
        if download_dir and os.path.exists(download_dir):
            shutil.rmtree(download_dir, ignore_errors=True)
        if extract_dir and os.path.exists(extract_dir):
            shutil.rmtree(extract_dir, ignore_errors=True)


def import_full_dump(workers: int = 4) -> list[dict]:
    """
    Download latest full dump from FTP and import into ClickHouse.

    Args:
        workers: Number of parallel workers for loading

    Returns:
        List of result messages for the response queue
    """
    return _import_dump("full", workers)


def import_incremental_dump(workers: int = 4) -> list[dict]:
    """
    Download latest incremental dump from FTP and import into ClickHouse.

    Args:
        workers: Number of parallel workers for loading

    Returns:
        List of result messages for the response queue
    """
    return _import_dump("incremental", workers)


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

    # Capture deletion cutoff before processing any entities
    deletion_cutoff = None
    temp_manager = StatsCacheManager(cache_config, ENTITY_CONFIGS[entities_to_process[0]])
    temp_manager.connect()
    deletion_cutoff = temp_manager.get_deletion_cutoff()
    if deletion_cutoff:
        logger.info(f"Deletion cutoff timestamp: {deletion_cutoff}")

    last_manager = None
    for entity_type in entities_to_process:
        try:
            entity_config = ENTITY_CONFIGS[entity_type]
            manager = StatsCacheManager(cache_config, entity_config)
            manager.connect()
            last_manager = manager

            # Use RMQ mode - yield messages as they're generated
            message_count = 0
            for message in manager.run_hourly_job_for_rmq(batch_size=batch_size, deletion_cutoff=deletion_cutoff):
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

    # Mark deletions as processed after all entities are done
    if deletion_cutoff is not None and last_manager is not None:
        logger.info(f"Marking deletions as processed up to {deletion_cutoff}")
        last_manager.mark_deletions_processed(cutoff=deletion_cutoff)

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


def cleanup_old_deletions(days: int = 7) -> list[dict]:
    """Clean up processed deletions older than N days."""
    cache_config = _get_cache_config()

    try:
        manager = StatsCacheManager(cache_config, ENTITY_CONFIGS['artist'])
        manager.connect()
        manager.cleanup_old_deletions(days=days)

        return [{
            'type': 'clickhouse_cleanup_deletions',
            'status': 'success',
            'days': days,
        }]
    except Exception as e:
        logger.error(f"Error cleaning up deletions: {e}", exc_info=True)
        return [{
            'type': 'clickhouse_cleanup_deletions',
            'status': 'error',
            'error': str(e),
        }]
