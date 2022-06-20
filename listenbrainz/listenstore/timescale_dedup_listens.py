"""
Utility tool for de-duplicating listens for which were submitted multiple times with
different casing for track names. It can be run multiple times.

1. take the min(listened_at)
2. work in chunks of 432000 seconds (5 days, this is the size of a timescale hypertable)
3. fetch tracks for deletion and then batch delete those using execute_values
"""
import math
import time
from datetime import datetime, timedelta

import psycopg2.extras
from sqlalchemy import text

from listenbrainz.db import timescale
from listenbrainz.listenstore import LISTEN_MINIMUM_TS

CHUNK_SECONDS = 432000


def process_chunk(chunk_start):
    chunk_start_dt = datetime.fromtimestamp(chunk_start)
    chunk_start_dt = chunk_start_dt.replace(microsecond=0)
    chunk_end_dt = datetime.fromtimestamp(chunk_start + CHUNK_SECONDS)
    chunk_end_dt = chunk_end_dt.replace(microsecond=0)
    print(f"Processing chunk: {chunk_start_dt.isoformat()} - {chunk_end_dt.isoformat()}")

    with timescale.engine.connect() as connection:
        result = connection.execute(text("""
            WITH all_tracks AS (
                SELECT listened_at
                     , user_id
                     , track_name
                     , row_number() over (PARTITION BY listened_at, user_id, lower(track_name)) AS rnum
                  FROM listen
                 WHERE listened_at >= :start AND listened_at < :end
            ) SELECT listened_at, user_id, track_name
                FROM all_tracks
               WHERE rnum > 1
        """), start=chunk_start, end=chunk_start + CHUNK_SECONDS)
        if result.rowcount == 0:
            print(" - No more items in this chunk")
            return
        else:
            rows_to_delete = [(row['listened_at'], row['user_id'], row['track_name']) for row in result]
            print(f" - got {len(rows_to_delete)} rows to delete")

    s = time.monotonic()
    dbapi_conn = timescale.engine.raw_connection()
    try:
        cursor = dbapi_conn.cursor()
        query = """
            DELETE FROM listen l
                  USING (VALUES %%s) d (listened_at, user_id, track_name)
                  WHERE l.listened_at = d.listened_at
                    AND l.user_id = d.user_id
                    AND l.track_name = d.track_name
        """
        # Push in chunk boundaries
        query = cursor.mogrify(query, (chunk_start, chunk_start + CHUNK_SECONDS))
        psycopg2.extras.execute_values(cursor, query, rows_to_delete)
        dbapi_conn.commit()
    finally:
        dbapi_conn.close()
    e = time.monotonic()
    print(f" - processed chunk in {round(e-s, 2)}s")

    return True


def dedup_listens():
    with timescale.engine.connect() as connection:
        result = connection.execute(
            text("""
               SELECT min(listened_at) as min_listened_at
                    , max(listened_at) as max_listened_at
                 FROM listen
                WHERE listened_at >= :least_accepted_ts"""),
            least_accepted_ts=LISTEN_MINIMUM_TS)
        row = result.fetchone()
        min_listened_at = row['min_listened_at']
        max_listened_at = row['max_listened_at']

    if min_listened_at is None:
        print("No chunks found for processing.")
        return

    number_chunks = math.ceil((max_listened_at - min_listened_at) / CHUNK_SECONDS)
    chunk_count = 0
    start_time = time.monotonic()
    chunk_start = min_listened_at
    while chunk_start < max_listened_at:
        result = process_chunk(chunk_start)
        if result is not True:
            # If we quit early, then remove this chunk from the count
            # so that completion time is more accurate
            number_chunks -= 1
        else:
            chunk_count += 1
        print_status_update(chunk_count, number_chunks, start_time)
        chunk_start += CHUNK_SECONDS

    print("Finished.")


def print_status_update(chunk_count, number_chunks, start_time):
    """Print a basic status update based on how many chunks have been computed"""
    if number_chunks > 0:
        chunk_time = time.monotonic()
        chunk_percentage = chunk_count / number_chunks
        duration = round(chunk_time - start_time)
        durdelta = timedelta(seconds=duration)
        remaining = round((duration / (chunk_percentage or 0.01)) - duration)
        remdelta = timedelta(seconds=remaining)
        print(f" - Done {chunk_count}/{number_chunks} in {str(durdelta)}; {str(remdelta)} remaining")
    else:
        print(f" No chunks processed")
