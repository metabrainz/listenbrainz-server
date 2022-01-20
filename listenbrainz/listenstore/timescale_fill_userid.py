"""
Utility tool for LB-866 - Use user ids in the listen table instead of usernames

This script fills in the timescale listens table to add a value to the user_id column
based on a listen's user_name. It can be run multiple times.
First, the 2021-08-03-listens-add-user-id.sql migration has to be applied

1. take the min(listened_at)
2. work in chunks of 432000 seconds (5 days, this is the size of a timescale hypertable)
3. See if this chunk has any rows where there are any null values for user_id. If none, skip to next chunk
4. Get a mapping of username -> userid for all rows that have a null user_id
5. Looping over each username, update the table to fill in user_id for this specific chunk. Loop to next chunk
"""
import math
import time
from datetime import datetime, timedelta

import psycopg2.extras
from sqlalchemy import text

from listenbrainz import db
from listenbrainz.db import timescale
from listenbrainz.listenstore import LISTEN_MINIMUM_TS

CHUNK_SECONDS = 432000
global_missing_users = set()

def process_chunk(chunk_start):
    chunk_start_dt = datetime.fromtimestamp(chunk_start)
    chunk_start_dt = chunk_start_dt.replace(microsecond=0)
    chunk_end_dt = datetime.fromtimestamp(chunk_start + CHUNK_SECONDS)
    chunk_end_dt = chunk_end_dt.replace(microsecond=0)
    print(f"Processing chunk: {chunk_start_dt.isoformat()} - {chunk_end_dt.isoformat()}")

    with timescale.engine.connect() as connection:
        result = connection.execute(
            text("""SELECT distinct(user_name) 
                      FROM listen 
                     WHERE user_id = 0 
                       AND listened_at >= :start 
                       AND listened_at < :end"""),
            start=chunk_start, end=chunk_start + CHUNK_SECONDS
        )
        if result.rowcount == 0:
            print(" - No more items in this chunk")
            return
        else:
            usernames = [row['user_name'] for row in result]
            print(f" - got {len(usernames)} usernames to process")

    # Get username -> user_id mappings from main user db
    with db.engine.connect() as connection:
        username_mapping_result = connection.execute(
            text("""SELECT id
                         , musicbrainz_id 
                      FROM "user"
                      WHERE musicbrainz_id in :ids"""),
            ids=tuple(usernames)
        )
        user_mapping = {row["musicbrainz_id"]: row["id"] for row in username_mapping_result}

    missing_users = set(usernames) - set(user_mapping.keys())
    if missing_users:
        # If we have listens with a username that isn't in the user table, report it but only
        # if we haven't seen these usernames before
        if missing_users - global_missing_users:
            global_missing_users.update(missing_users)
            print(f" - oops - found some usernames who have listens but no user row")
            print(f"   all missing users are now {global_missing_users}")

    if not user_mapping:
        print(" - Unexpectedly have no user mapping even after validation")
        return

    s = time.monotonic()
    dbapi_conn = timescale.engine.raw_connection()
    try:
        cursor = dbapi_conn.cursor()
        query = """UPDATE listen AS t SET user_id = e.user_id
                     FROM (values %%s) AS e (user_name, user_id)
                    WHERE e.user_name = t.user_name
                      AND t.listened_at >= %s 
                      AND t.listened_at < %s"""
        # Push in chunk boundaries
        query = cursor.mogrify(query, (chunk_start, chunk_start + CHUNK_SECONDS))
        psycopg2.extras.execute_values(cursor, query, user_mapping.items(), template=None, page_size=100)
        dbapi_conn.commit()
    finally:
        dbapi_conn.close()
    e = time.monotonic()
    print(f" - processed chunk in {round(e-s, 2)}s")

    return True


def fill_userid():
    with timescale.engine.connect() as connection:
        result = connection.execute(
            text("""
               SELECT min(listened_at) as min_listened_at
                    , max(listened_at) as max_listened_at
                 FROM listen
                WHERE listened_at >= :least_accepted_ts
                  AND user_id = 0"""),
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
    print(f"Usernames who have listens but no known user row: {global_missing_users}")


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
