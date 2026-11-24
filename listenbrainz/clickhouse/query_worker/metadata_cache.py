"""Refresh ClickHouse metadata from the same PostgreSQL sources as Spark."""

import logging
from contextlib import closing
from uuid import uuid4

from brainzutils import musicbrainz_db
from clickhouse_connect.driver import Client
from sqlalchemy import text
from sqlalchemy.engine import Engine

from listenbrainz import db
from listenbrainz.clickhouse.query_worker.client import ClickHouseConnection
from listenbrainz.clickhouse.query_worker.metadata_tables import MUSICBRAINZ_TABLES, RECORDING_FEEDBACK, MetadataTable


logger = logging.getLogger(__name__)
BATCH_SIZE = 50_000


def _refresh_table(client: Client, source: Engine, table: MetadataTable):
    logger.info("Refreshing %s", table.name)
    definition = f"({table.columns}) ENGINE = MergeTree ORDER BY {table.order_by}"
    query = text(table.query).execution_options(yield_per=BATCH_SIZE)
    try:
        with source.connect() as conn, conn.execute(query, table.parameters) as rows:
            client.command(f"CREATE TEMPORARY TABLE metadata_load {definition}")
            insert = client.create_insert_context("metadata_load", column_names=list(rows.keys()))
            for batch in rows.partitions(BATCH_SIZE):
                client.insert(data=batch, context=insert)
        client.command(f"CREATE TABLE IF NOT EXISTS {table.name} {definition}")
        # An unpartitioned MergeTree has one partition, identified by tuple().
        client.command(f"ALTER TABLE {table.name} REPLACE PARTITION tuple() FROM metadata_load "
                       "SETTINGS max_partition_size_to_drop = 0")
    finally:
        client.command("DROP TEMPORARY TABLE IF EXISTS metadata_load SETTINGS max_table_size_to_drop = 0")


def update_metadata_cache():
    """Publish one complete snapshot per cache, including feedback from ListenBrainz."""
    connection = ClickHouseConnection.from_config()
    with closing(connection.connect(session_id=uuid4().hex, settings={"session_timeout": 3600},
                                    send_receive_timeout=7200)) as client:
        if musicbrainz_db.engine is None:
            logger.info("Skipping MusicBrainz metadata caches because MB_DATABASE_URI is unconfigured")
        else:
            for table in MUSICBRAINZ_TABLES:
                _refresh_table(client, musicbrainz_db.engine, table)
        _refresh_table(client, db.engine, RECORDING_FEEDBACK)
