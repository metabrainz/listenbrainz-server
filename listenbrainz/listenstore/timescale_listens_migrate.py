"""
Utility tool for migrating listens to new schema table. It can be run multiple times.
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


def process_created(created: datetime):
    print("Fixing-up using created - this may take a while.")
    query = """
        INSERT INTO listen_new (listened_at, created, user_id, recording_msid, data)
             SELECT to_timestamp(listened_at)
                  , created
                  , user_id
                  , (data->'track_metadata'->'additional_info'->>'recording_msid')::uuid
                  , jsonb_set(data->'track_metadata', '{track_name}'::text[], to_jsonb(track_name), true) #- '{additional_info,recording_msid}'::text[]
               FROM listen
              WHERE listened_at >= :start
                AND created >= :last_created
           ORDER BY listened_at ASC  
        ON CONFLICT (listened_at, user_id, recording_msid)
         DO NOTHING
    """
    s = time.monotonic()
    with timescale.engine.connect() as connection:
        connection.execute(text(query), {"start": LISTEN_MINIMUM_TS, "last_created": created})
    e = time.monotonic()

    print(f" - fixed up using created in {round(e-s, 2)}s")

def process_chunk(chunk_start):
    chunk_start_dt = datetime.fromtimestamp(chunk_start)
    chunk_start_dt = chunk_start_dt.replace(microsecond=0)
    chunk_end_dt = datetime.fromtimestamp(chunk_start + CHUNK_SECONDS)
    chunk_end_dt = chunk_end_dt.replace(microsecond=0)
    print(f"Processing chunk: {chunk_start_dt.isoformat()} - {chunk_end_dt.isoformat()}")

    query = """
        INSERT INTO listen_new (listened_at, created, user_id, recording_msid, data)
             SELECT to_timestamp(listened_at)
                  , created
                  , user_id
                  , (data->'track_metadata'->'additional_info'->>'recording_msid')::uuid
                  , jsonb_set(data->'track_metadata', '{track_name}'::text[], to_jsonb(track_name), true) #- '{additional_info,recording_msid}'::text[]
               FROM listen
              WHERE listened_at >= :start 
                AND listened_at < :end
           ORDER BY listened_at ASC  
        ON CONFLICT (listened_at, user_id, recording_msid)
         DO NOTHING
    """
    s = time.monotonic()
    with timescale.engine.connect() as connection:
        connection.execute(text(query), {"start": chunk_start, "end": chunk_start + CHUNK_SECONDS})
    e = time.monotonic()

    print(f" - processed chunk in {round(e-s, 2)}s")


def migrate_listens():
    query1 = """
        SELECT min(listened_at) as min_listened_at
             , max(listened_at) as max_listened_at
          FROM listen
         WHERE listened_at >= :least_accepted_ts
    """
    query2 = """
        SELECT COALESCE(EXTRACT('epoch' from max(listened_at)), 0) AS already_done_ts
             , max(created) AS already_max_created
          FROM listen_new
    """
    with timescale.engine.connect() as connection:
        result = connection.execute(text(query1), {"least_accepted_ts": LISTEN_MINIMUM_TS})
        row = result.fetchone()
        max_listened_at = row.max_listened_at

        result = connection.execute(text(query2))
        row = result.fetchone()
        already_done_ts = row.already_done_ts
        already_max_created = row.already_max_created

    if already_done_ts:
        chunk_start = already_done_ts - already_done_ts % CHUNK_SECONDS
    else:
        chunk_start = LISTEN_MINIMUM_TS

    number_chunks = math.ceil((max_listened_at - chunk_start) / CHUNK_SECONDS)
    chunk_count = 0
    start_time = time.monotonic()
    while chunk_start < max_listened_at:
        process_chunk(chunk_start)
        chunk_count += 1
        print_status_update(chunk_count, number_chunks, start_time)
        chunk_start += CHUNK_SECONDS

    # since listens with older listened_at values can be inserted between runs, also do a scan with created field
    # to insert the remaining listens
    if already_max_created:
        print("Finished chunkwise scan.")
        process_created(already_max_created)

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
