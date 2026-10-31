"""Handlers for the jobs of the ClickHouse query worker (see query_map)."""

import logging
from contextlib import closing
from typing import Optional

from flask import current_app

from listenbrainz.clickhouse.query_worker.client import ClickHouseConnection
from listenbrainz.clickhouse.query_worker.listens.ftp import get_ftp_downloader
from listenbrainz.clickhouse.query_worker.listens.load_dump import (
    import_full_dump as load_full_dump, import_missing_incremental_dumps,
)
from listenbrainz.clickhouse.query_worker.listens.schema import ensure_schema
from listenbrainz.clickhouse.query_worker.utils import describe_load_errors

logger = logging.getLogger(__name__)


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
        'added': result['added'],
        'files_completed': result['files_completed'],
        **fields,
    }


def init_schema() -> list[dict]:
    """Create the ClickHouse schema."""
    try:
        with _client() as ch_client:
            ensure_schema(ch_client)
    except Exception as e:
        return _error('clk_schema_initialized', e)
    return [{'type': 'clk_schema_initialized', 'status': 'success'}]


def import_full_dump(workers: int = 4, dump_id: Optional[int] = None) -> list[dict]:
    """Download the selected or latest full dump from FTP, replacing listens."""
    try:
        result = load_full_dump(
            ClickHouseConnection.from_config(),
            get_ftp_downloader(current_app),
            workers=workers,
            dump_id=dump_id,
            download_dir=current_app.config["CLICKHOUSE_DUMP_DOWNLOAD_DIR"],
        )
        _raise_on_load_errors(result)
    except Exception as e:
        return _error('clk_dump_imported', e, dump_type='full')
    return [_dump_imported('full', result)]


def import_incremental_dump(workers: int = 4, max_dumps: Optional[int] = None,
                            dump_id: Optional[int] = None) -> list[dict]:
    """Import a selected incremental dump or catch up oldest first.

    Stops at the first failure so that dump is retried next run. ``max_dumps`` limits how
    many are loaded in this run; ``dump_id`` selects one exact dump instead.
    """
    try:
        result = import_missing_incremental_dumps(
            ClickHouseConnection.from_config(),
            get_ftp_downloader(current_app),
            workers=workers,
            max_dumps=max_dumps,
            dump_id=dump_id,
            download_dir=current_app.config["CLICKHOUSE_DUMP_DOWNLOAD_DIR"],
        )
    except Exception as e:
        return _error('clk_dump_imported', e, dump_type='incremental')

    messages = [
        _dump_imported('incremental', dump, pending=dump['pending'])
        for dump in result['imported']
    ]
    messages.extend({
        'type': 'clk_dump_imported',
        'dump_type': 'incremental',
        'status': 'error',
        'dump_id': dump_id,
        'pending': result['pending'],
        'error': error,
    } for dump_id, error in result['errors'])

    if not messages:
        logger.info("No incremental dumps to import")
    return messages
