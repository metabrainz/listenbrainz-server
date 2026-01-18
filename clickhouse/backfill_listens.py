#!/usr/bin/env python3
"""
ClickHouse Listen Backfiller - Simplified

This script reads listens directly from the TimescaleDB `listen` table,
enchriches them with mapping and metadata, and inserts them into the
ClickHouse `listens` table.

It's designed for backfilling historical data. It processes listens in batches
ordered by listened_at, using the timestamp of the last processed listen to
fetch the next batch.
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

# This query fetches a batch of listens and enriches them in one go.
# It uses a `listens_to_process` CTE to select a batch of listens
# starting after a specific timestamp, which allows for pagination.
LISTEN_ENRICHMENT_QUERY = """
    WITH listens_to_process AS (
        SELECT listened_at, created, user_id, recording_msid, data
          FROM listen
         WHERE listened_at > %s
      ORDER BY listened_at
         LIMIT %s
    ),
    listen_with_mbid AS (
        SELECT l.listened_at
             , l.created::timestamp(3) with time zone AS created
             , l.user_id
             , l.recording_msid
             , l.data->'additional_info'->'artist_mbids' AS l_artist_credit_mbids
             , l.data->>'artist_name' AS l_artist_name
             , l.data->>'release_name' AS l_release_name
             , l.data->'additional_info'->>'release_mbid' AS l_release_mbid
             , l.data->>'track_name' AS l_recording_name
             , l.data->'additional_info'->>'recording_mbid' AS l_recording_mbid
             -- prefer to use user specified mapping, then mbid mapper's mapping, finally other user's specified mappings
             , COALESCE(user_mm.recording_mbid, mm.recording_mbid, other_mm.recording_mbid) AS m_recording_mbid
          FROM listens_to_process l
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
  ORDER BY listened_at
"""


class ClickHouseBackfiller:
    """Backfills listens from TimescaleDB to ClickHouse."""

    def __init__(self):
        self.ch_client: Optional[Client] = None
        self.ts_conn = None
        self.batch_size = 1000  # Number of listens to process in each batch

    def init_clickhouse(self):
        """Initialize ClickHouse connection."""
        self.ch_client = clickhouse_connect.get_client(
            host=config.CLICKHOUSE_HOST,
            port=config.CLICKHOUSE_PORT,
            database=config.CLICKHOUSE_DATABASE,
            username=config.CLICKHOUSE_USERNAME,
            password=config.CLICKHOUSE_PASSWORD,
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

    def _fetch_enriched_batch(self, last_listened_at: datetime) -> list[dict]:
        """Fetches and enriches a batch of listens directly from TimescaleDB."""
        try:
            with self.ts_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as curs:
                curs.execute(LISTEN_ENRICHMENT_QUERY, (last_listened_at, self.batch_size))
                rows = curs.fetchall()
            self.ts_conn.rollback()
            return rows
        except Exception as e:
            logger.error(f"Error fetching enriched batch from TimescaleDB: {e}", exc_info=True)
            self.ts_conn.rollback()
            return []

    def _transform_enriched_rows(self, rows: list[dict]) -> list[dict]:
        """Transforms raw enriched rows into the final format for ClickHouse."""
        transformed = []
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

            transformed.append({
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
        return transformed

    def _insert_to_clickhouse(self, enriched_listens: list[dict]):
        """Inserts a batch of enriched listens into ClickHouse."""
        if not enriched_listens:
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
            for listen in enriched_listens
        ]

        self.ch_client.insert('listens', rows, column_names=columns)

    def run(self):
        """Main method to run the backfill process."""
        try:
            self.init_clickhouse()
            self.init_timescale()

            # Find the starting point for the backfill
            with self.ts_conn.cursor() as curs:
                curs.execute("SELECT min(listened_at) FROM listen")
                res = curs.fetchone()
                if res and res[0]:
                    # Start from just before the very first listen to include it
                    last_listened_at = res[0] - timedelta(microseconds=1)
                else:
                    logger.info("No listens found in the listen table to backfill.")
                    return
            self.ts_conn.rollback()  # End the transaction

            logger.info(f"Starting backfill from {last_listened_at}")

            total_processed = 0
            progress_report_count = 0

            while True:
                enriched_rows = self._fetch_enriched_batch(last_listened_at)

                if not enriched_rows:
                    logger.info("No more listens to process.")
                    break

                transformed_listens = self._transform_enriched_rows(enriched_rows)
                self._insert_to_clickhouse(transformed_listens)

                batch_size = len(transformed_listens)
                total_processed += batch_size
                last_listened_at = transformed_listens[-1]['listened_at']

                # Report progress every 100k listens
                if total_processed >= progress_report_count + 100000:
                    progress_report_count = (total_processed // 100000) * 100000
                    logger.info(f"Processed {progress_report_count} listens... Last timestamp: {last_listened_at}")

            logger.info(f"Backfill completed. Total listens processed: {total_processed}")

        except Exception as e:
            logger.critical(f"An unhandled error occurred: {e}", exc_info=True)
        finally:
            if self.ts_conn:
                self.ts_conn.close()
            if self.ch_client:
                self.ch_client.close()


def main():
    """Entry point for the script."""
    backfiller = ClickHouseBackfiller()
    backfiller.run()


if __name__ == '__main__':
    main()