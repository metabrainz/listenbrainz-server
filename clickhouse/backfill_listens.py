#!/usr/bin/env python3
"""
ClickHouse Listen Backfiller

This script reads listens directly from the TimescaleDB `listen` table,
enchriches them with mapping and metadata, and inserts them into the
ClickHouse `listens` table.

It's designed for backfilling historical data, processing listens one day
at a time. This is similar to clickhouse/listen_consumer.py, but reads
from the database instead of RabbitMQ.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import clickhouse_connect
import psycopg2
import psycopg2.extras
from clickhouse_connect.driver import Client

import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Copied from listen_consumer.py
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


class ClickHouseBackfiller:
    """Backfills listens from TimescaleDB to ClickHouse."""

    def __init__(self):
        self.ch_client: Optional[Client] = None
        self.ts_conn = None
        self.batch_size = 1000

    def init_clickhouse(self):
        """Initialize ClickHouse connection."""
        self.ch_client = clickhouse_connect.get_client(
            host=config.CLICKHOUSE_HOST,
            port=config.CLICKHOUSE_PORT,
            database=config.CLICKHOUSE_DATABASE,
            username=config.CLICKHOUSE_USERNAME,
            password=config.CLICKHOUSE_PASSWORD,
            # Disable async insert for a batch script
        )
        logger.info(f"Connected to ClickHouse at {config.CLICKHOUSE_HOST}:{config.CLICKHOUSE_PORT}")

    def init_timescale(self):
        """Initialize TimescaleDB connection."""
        self.ts_conn = psycopg2.connect(
            host=config.TIMESCALE_HOST,
            port=config.TIMESCALE_PORT,
            database=config.TIMESCALE_DATABASE,
            user=config.TIMESCALE_USERNAME,
            password=config.TIMESCALE_PASSWORD,
        )
        logger.info(f"Connected to TimescaleDB at {config.TIMESCALE_HOST}:{config.TIMESCALE_PORT}")

    def enrich_listens(self, listen_keys: list) -> list[dict]:
        """
        Query TimescaleDB to get full listen data with mapping info.

        Args:
            listen_keys: List of listen key tuples (user_id, listened_at, recording_msid)

        Returns:
            List of enriched listen dicts ready for ClickHouse insertion
        """
        if not listen_keys:
            return []

        # Query TimescaleDB for enriched data using execute_values
        enriched = []
        try:
            with self.ts_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as curs:
                rows = psycopg2.extras.execute_values(
                    curs,
                    LISTEN_ENRICHMENT_QUERY,
                    listen_keys,
                    template="(%s::int, %s::timestamptz, %s::uuid)",
                    fetch=True,
                )

                for row in rows:
                    is_mapped = row['artist_credit_id'] is not None
                    if is_mapped:
                        artist_name = row['m_artist_name']
                        release_name = row['m_release_name']
                        recording_name = row['m_recording_name']
                        artist_credit_id = row['artist_credit_id']
                        artist_credit_mbids = row['m_artist_credit_mbids'] or []
                        release_mbid = row['m_release_mbid'] or ''
                        recording_mbid = row['m_recording_mbid'] or ''
                        artist_mb_ids = row['m_artist_mb_ids'] or []
                    else:
                        artist_name = row['l_artist_name']
                        release_name = row['l_release_name'] or ''
                        recording_name = row['l_recording_name']
                        artist_credit_id = 0
                        artist_credit_mbids = row['l_artist_credit_mbids'] or []
                        release_mbid = row['l_release_mbid'] or ''
                        recording_mbid = row['l_recording_mbid'] or ''
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
            try:
                self.ts_conn.rollback()
            except Exception:
                pass

        return enriched

    def process_batch(self, listen_keys: list):
        """Enrich a batch of listens and insert them into ClickHouse."""
        if not listen_keys:
            return

        try:
            enriched = self.enrich_listens(listen_keys)

            if not enriched:
                logger.warning(f"No listens enriched from batch of {len(listen_keys)}")
                return

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

            logger.debug(f"Inserted {len(enriched)} listens into ClickHouse.")

        except Exception as e:
            logger.error(f"Error processing batch: {e}", exc_info=True)

    def backfill_day(self, day: datetime.date):
        """Backfill all listens for a specific day."""
        logger.info(f"Backfilling listens for {day}")
        day_start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)

        # Using a named cursor for server-side processing to avoid loading all rows into memory at once
        with self.ts_conn.cursor(name='listen_cursor') as curs:
            curs.itersize = self.batch_size  # fetch this many rows at a time
            curs.execute("""
                SELECT user_id, listened_at, recording_msid
                FROM listen
                WHERE listened_at >= %s AND listened_at < %s
            """, (day_start, day_end))

            batch = []
            processed_count = 0
            for row in curs:
                batch.append(row)
                if len(batch) >= self.batch_size:
                    self.process_batch(batch)
                    processed_count += len(batch)
                    logger.info(f"  ... processed {processed_count} listens for {day}")
                    batch = []

            if batch:
                self.process_batch(batch)
                processed_count += len(batch)

        logger.info(f"Finished day {day}, total listens: {processed_count}")

    def run(self):
        """Main method to run the backfill process."""
        try:
            self.init_clickhouse()
            self.init_timescale()

            with self.ts_conn.cursor() as curs:
                curs.execute("SELECT min(listened_at)::date, max(listened_at)::date FROM listen")
                res = curs.fetchone()
                if not res:
                    logger.info("No listens found in the listen table.")
                    return
                start_date, end_date = res

            if not start_date or not end_date:
                logger.info("No listens found in the listen table.")
                return

            logger.info(f"Starting backfill from {start_date} to {end_date}")

            current_date = start_date
            while current_date <= end_date:
                self.backfill_day(current_date)
                current_date += timedelta(days=1)
                # Commit after each day to free up resources on the PostgreSQL server.
                self.ts_conn.commit()

            logger.info("Backfill completed.")

        except Exception as e:
            logger.critical(f"An unhandled error occurred: {e}", exc_info=True)
        finally:
            if self.ts_conn:
                self.ts_conn.close()


def main():
    """Entry point for the script."""
    backfiller = ClickHouseBackfiller()
    backfiller.run()


if __name__ == '__main__':
    main()
