#!/usr/bin/env python3
"""
ClickHouse Listen Consumer

Consumes deduplicated listens from the UNIQUE_EXCHANGE queue
and inserts them into the ClickHouse listens table.

This consumer listens to the same exchange that other consumers
(WebSocket dispatcher, MBID mapping writer, etc.) use, but with
its own dedicated queue for ClickHouse ingestion.

For each batch of listens received, it queries TimescaleDB to get:
- The `created` timestamp from the listen table
- MBID mapping data (recording_mbid, artist_mbids, etc.)
- Metadata from mb_metadata_cache (artist_credit_id, etc.)

This follows the same data enrichment pattern as the spark dump.
"""

import json
import logging
import socket
import time
from datetime import datetime, timezone
from typing import Optional

import clickhouse_connect
import psycopg2
import psycopg2.extras
from clickhouse_connect.driver import Client
from kombu import Connection, Exchange, Queue
from kombu.mixins import ConsumerMixin

import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Query to get full listen data with mapping, similar to spark dump
# Uses VALUES clause populated by execute_values for efficient batch lookup
# Also looks up MB integer artist IDs from the artist table
LISTEN_ENRICHMENT_QUERY = """
    WITH listen_keys (user_id, listened_at, recording_msid) AS (VALUES %s),
    listen_with_mbid AS (
        SELECT l.listened_at
             , l.created::timestamp(3) with time zone AS created
             , l.user_id
             , l.recording_msid
             , data->'additional_info'->'artist_mbids' AS l_artist_credit_mbids
             , data->>'artist_name' AS l_artist_name
             , data->>'release_name' AS l_release_name
             , data->'additional_info'->>'release_mbid' AS l_release_mbid
             , data->>'track_name' AS l_recording_name
             , data->'additional_info'->>'recording_mbid' AS l_recording_mbid
             -- prefer to use user specified mapping, then mbid mapper's mapping, finally other user's specified mappings
             , COALESCE(user_mm.recording_mbid, mm.recording_mbid, other_mm.recording_mbid) AS m_recording_mbid
          FROM listen l
          JOIN listen_keys lk
            ON l.user_id = lk.user_id
           AND l.listened_at = lk.listened_at
           AND l.recording_msid = lk.recording_msid
     LEFT JOIN mbid_mapping mm
            ON l.recording_msid = mm.recording_msid
     LEFT JOIN mbid_manual_mapping user_mm
            ON l.recording_msid = user_mm.recording_msid
           AND user_mm.user_id = l.user_id
     LEFT JOIN mbid_manual_mapping_top other_mm
            ON l.recording_msid = other_mm.recording_msid
    ),
    -- Look up MB integer artist IDs from artist_mbids array
    listen_with_artist_ids AS (
        SELECT l.*
             , mbc.artist_mbids AS m_artist_mbids
             , (mbc.artist_data->'artist_credit_id')::INT AS artist_credit_id
             , mbc.artist_data->>'name' AS m_artist_name
             , COALESCE(mbc.release_mbid::TEXT, '') AS m_release_mbid
             , COALESCE(mbc.release_data->>'name', '') AS m_release_name
             , mbc.recording_data->>'name' AS m_recording_name
             -- Get artist IDs by looking up each MBID in the artist table
             , COALESCE(
                   (SELECT array_agg(COALESCE(a.id, 0) ORDER BY idx)
                    FROM unnest(mbc.artist_mbids) WITH ORDINALITY AS u(mbid, idx)
                    LEFT JOIN mapping.mb_artist_id_gid_cache_tmp a ON a.gid = u.mbid),
                   ARRAY[]::INT[]
               ) AS m_artist_mb_ids
          FROM listen_with_mbid l
     LEFT JOIN mapping.mb_metadata_cache mbc
            ON l.m_recording_mbid = mbc.recording_mbid
    )
    SELECT listened_at
         , created
         , user_id
         , recording_msid::TEXT
         , l_artist_credit_mbids
         , l_artist_name
         , l_release_name
         , l_release_mbid
         , l_recording_name
         , l_recording_mbid
         , m_recording_mbid::TEXT
         , artist_credit_id
         , m_artist_mbids::TEXT[] AS m_artist_credit_mbids
         , m_artist_name
         , m_release_mbid
         , m_release_name
         , m_recording_name
         , m_artist_mb_ids
      FROM listen_with_artist_ids
"""


class ClickHouseListenConsumer(ConsumerMixin):
    """Consumer for real-time listen ingestion into ClickHouse."""

    def __init__(self):
        self.connection = None
        self.ch_client: Optional[Client] = None
        self.ts_conn = None

        # Listen to the UNIQUE_EXCHANGE with our own queue
        self.unique_exchange = Exchange(
            config.UNIQUE_EXCHANGE,
            "fanout",
            durable=False
        )
        self.listen_queue = Queue(
            config.CLICKHOUSE_LISTEN_QUEUE,
            exchange=self.unique_exchange,
            durable=True
        )

        # Batch settings for efficient inserts
        self.batch_size = 100
        self.batch_timeout = 5.0  # seconds
        self.pending_listens = []  # Raw listens from RMQ
        self.last_flush_time = time.time()

    def init_clickhouse(self):
        """Initialize ClickHouse connection."""
        self.ch_client = clickhouse_connect.get_client(
            host=config.CLICKHOUSE_HOST,
            port=config.CLICKHOUSE_PORT,
            database=config.CLICKHOUSE_DATABASE,
            username=config.CLICKHOUSE_USERNAME,
            password=config.CLICKHOUSE_PASSWORD,
            settings={
                "async_insert": 1,
                "wait_for_async_insert": 0,
            },
        )
        logger.info(f"Connected to ClickHouse at {config.CLICKHOUSE_HOST}:{config.CLICKHOUSE_PORT}")

    def init_timescale(self):
        """Initialize TimescaleDB connection for mapping data lookup."""
        self.ts_conn = psycopg2.connect(
            host=config.TIMESCALE_HOST,
            port=config.TIMESCALE_PORT,
            database=config.TIMESCALE_DATABASE,
            user=config.TIMESCALE_USERNAME,
            password=config.TIMESCALE_PASSWORD,
        )
        logger.info(f"Connected to TimescaleDB at {config.TIMESCALE_HOST}:{config.TIMESCALE_PORT}")

    def enrich_listens(self, listens: list[dict]) -> list[dict]:
        """
        Query TimescaleDB to get full listen data with mapping info.

        Takes raw listens from RMQ (which have user_id, timestamp, recording_msid)
        and enriches them with:
        - created timestamp from the listen table
        - MBID mapping data (recording_mbid, etc.)
        - Metadata from mb_metadata_cache (artist_credit_id, artist names, etc.)

        Args:
            listens: List of raw listen dicts from RMQ

        Returns:
            List of enriched listen dicts ready for ClickHouse insertion
        """
        if not listens:
            return []

        # Build values for execute_values: (user_id, listened_at, recording_msid)
        values = [
            (
                listen['user_id'],
                datetime.fromtimestamp(listen['timestamp'], tz=timezone.utc),
                listen['recording_msid'],
            )
            for listen in listens
        ]

        # Query TimescaleDB for enriched data using execute_values
        enriched = []
        try:
            with self.ts_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as curs:
                # Use execute_values with fetch=True to get results
                # Template casts the values to the correct types
                rows = psycopg2.extras.execute_values(
                    curs,
                    LISTEN_ENRICHMENT_QUERY,
                    values,
                    template="(%s::int, %s::timestamptz, %s::uuid)",
                    fetch=True,
                )

                for row in rows:
                    # Either take the mapping metadata or the original listen metadata
                    # is_mapped=True means data comes from MB mapping (trusted MBIDs)
                    # is_mapped=False means user-submitted data (MBIDs not trusted for grouping)
                    is_mapped = row['artist_credit_id'] is not None
                    if is_mapped:
                        artist_name = row['m_artist_name']
                        release_name = row['m_release_name']
                        recording_name = row['m_recording_name']
                        artist_credit_id = row['artist_credit_id']
                        artist_credit_mbids = row['m_artist_credit_mbids'] or []
                        release_mbid = row['m_release_mbid'] or ''
                        recording_mbid = row['m_recording_mbid'] or ''
                        # MB integer artist IDs from the artist table lookup
                        artist_mb_ids = row['m_artist_mb_ids'] or []
                    else:
                        artist_name = row['l_artist_name']
                        release_name = row['l_release_name'] or ''
                        recording_name = row['l_recording_name']
                        artist_credit_id = 0
                        artist_credit_mbids = row['l_artist_credit_mbids'] or []
                        release_mbid = row['l_release_mbid'] or ''
                        recording_mbid = row['l_recording_mbid'] or ''
                        # Unmapped listens have no MB artist IDs
                        artist_mb_ids = []

                    enriched.append({
                        'listened_at': row['listened_at'],
                        'created': row['created'],
                        'user_id': row['user_id'],
                        'recording_msid': row['recording_msid'],
                        'artist_name': artist_name,
                        'artist_credit_id': artist_credit_id,
                        'release_name': release_name,
                        'release_mbid': release_mbid,
                        'recording_name': recording_name,
                        'recording_mbid': recording_mbid,
                        'artist_credit_mbids': artist_credit_mbids,
                        'artist_mb_ids': artist_mb_ids,
                        'is_mapped': is_mapped,
                    })

        except Exception as e:
            logger.error(f"Error enriching listens from TimescaleDB: {e}", exc_info=True)
            # On error, reset connection for next attempt
            try:
                self.ts_conn.rollback()
            except Exception:
                pass

        return enriched

    def flush_batch(self):
        """Flush pending listens to ClickHouse."""
        if not self.pending_listens:
            return

        try:
            # Enrich listens with mapping data from TimescaleDB
            enriched = self.enrich_listens(self.pending_listens)
            for listen in enriched:
                print(listen)

            if not enriched:
                logger.warning(f"No listens enriched from batch of {len(self.pending_listens)}")
                self.pending_listens = []
                self.last_flush_time = time.time()
                return

            # Prepare column data
            columns = [
                'listened_at', 'created', 'user_id', 'recording_msid',
                'artist_name', 'artist_credit_id', 'release_name', 'release_mbid',
                'recording_name', 'recording_mbid', 'artist_credit_mbids',
                'artist_mb_ids', 'is_mapped'
            ]

            rows = [
                [
                    listen['listened_at'],
                    listen['created'],
                    listen['user_id'],
                    listen['recording_msid'],
                    listen['artist_name'],
                    listen['artist_credit_id'],
                    listen['release_name'],
                    listen['release_mbid'],
                    listen['recording_name'],
                    listen['recording_mbid'],
                    listen['artist_credit_mbids'],
                    listen['artist_mb_ids'],
                    listen['is_mapped'],
                ]
                for listen in enriched
            ]

            self.ch_client.insert(
                'listens',
                rows,
                column_names=columns,
            )

            logger.debug(f"Inserted {len(enriched)} listens into ClickHouse (from {len(self.pending_listens)} received)")
            self.pending_listens = []
            self.last_flush_time = time.time()

        except Exception as e:
            logger.error(f"Error flushing batch to ClickHouse: {e}", exc_info=True)
            # Keep the listens for retry
            # TODO: Implement proper retry logic with dead letter queue

    def maybe_flush(self):
        """Flush batch if size or timeout threshold reached."""
        if len(self.pending_listens) >= self.batch_size:
            self.flush_batch()
        elif self.pending_listens and (time.time() - self.last_flush_time) >= self.batch_timeout:
            self.flush_batch()

    def callback(self, body, message):
        """Handle incoming listen message."""
        try:
            data = json.loads(body)

            # Handle both single listen and batch formats
            listens = data if isinstance(data, list) else [data]

            # Store raw listens - they'll be enriched during flush
            for listen in listens:
                self.pending_listens.append(listen)

            self.maybe_flush()

        except Exception as e:
            logger.error(f"Error processing listen message: {e}", exc_info=True)
        finally:
            message.ack()

    def get_consumers(self, Consumer, channel):
        return [
            Consumer(
                queues=[self.listen_queue],
                on_message=lambda x: self.callback(x.body, x),
                prefetch_count=self.batch_size * 2,
            )
        ]

    def on_iteration(self):
        """Called on each consumer iteration - use for periodic flush."""
        self.maybe_flush()

    def init_rabbitmq_connection(self):
        """Initialize RabbitMQ connection."""
        connection_name = "clickhouse-listen-consumer-" + socket.gethostname()
        self.connection = Connection(
            hostname=config.RABBITMQ_HOST,
            userid=config.RABBITMQ_USERNAME,
            port=config.RABBITMQ_PORT,
            password=config.RABBITMQ_PASSWORD,
            virtual_host=config.RABBITMQ_VHOST,
            transport_options={"client_properties": {"connection_name": connection_name}}
        )

    def start(self):
        """Start the consumer."""
        while True:
            try:
                logger.info("ClickHouse listen consumer starting...")
                self.init_clickhouse()
                self.init_timescale()
                self.init_rabbitmq_connection()
                self.run()
            except Exception as e:
                logger.critical("Error in ClickHouse listen consumer: %s", str(e), exc_info=True)
                time.sleep(2)
            finally:
                # Flush any remaining listens before restart
                if self.pending_listens:
                    self.flush_batch()
                # Close TimescaleDB connection
                if self.ts_conn:
                    try:
                        self.ts_conn.close()
                    except Exception:
                        pass


def main():
    """Entry point for the consumer."""
    consumer = ClickHouseListenConsumer()
    consumer.start()


if __name__ == '__main__':
    main()
