"""
Utility tool for migrating listens to new schema table. It can be run multiple times.
"""
import math
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from listenbrainz.db import timescale

LISTEN_MINIMUM_DATE = datetime(2002, 10, 1)
CHUNK_SIZE = timedelta(days=30)
MAX_CREATED_WHEN_ENABLED_ON_TEST = datetime(2023, 11, 13, tzinfo=timezone.utc)


def process_created(created: datetime):
    print("Fixing-up using created - this may take a while.")
    query = """
        insert into listen_unique (listened_at, created, user_id, recording_msid, data)
             select listened_at
                  , created
                  , user_id
                  , coalesce(r.original_msid, l.recording_msid)
                  , jsonb_set(data, '{additional_info,recording_msid}'::text[], coalesce(r.original_msid, l.recording_msid)::jsonb)
               from listen l
          left join messybrainz.submissions_redirect r
                 on l.recording_msid = r.duplicate_msid
              where listened_at >= :start
                and created >= :last_created
           order by listened_at asc
        on conflict (listened_at, user_id, recording_msid)
         do nothing
    """
    s = time.monotonic()
    with timescale.engine.connect() as connection:
        connection.execute(text(query), {"start": LISTEN_MINIMUM_DATE, "last_created": created})
    e = time.monotonic()

    print(f" - fixed up using created in {round(e-s, 2)}s")


def process_chunk(chunk_start_dt):
    chunk_end_dt = chunk_start_dt + CHUNK_SIZE
    print(f"Processing chunk: {chunk_start_dt.isoformat()} - {chunk_end_dt.isoformat()}")

    query = """
        insert into listen_unique (listened_at, created, user_id, recording_msid, data)
             select listened_at
                  , created
                  , user_id
                  , coalesce(r.original_msid, l.recording_msid)
                  , jsonb_set(data, '{additional_info,recording_msid}'::text[], coalesce(r.original_msid, l.recording_msid)::jsonb)
               from listen l
          left join messybrainz.submissions_redirect r
                 on l.recording_msid = r.duplicate_msid
              where listened_at >= :start
                and listened_at < :end
           order by listened_at asc
        on conflict (listened_at, user_id, recording_msid)
         do nothing
    """

    s = time.monotonic()
    with timescale.engine.connect() as connection:
        connection.execute(text(query), {"start": chunk_start_dt, "end": chunk_end_dt})
    e = time.monotonic()

    print(f" - processed chunk in {round(e-s, 2)}s")


def deduplicate_listens():
    query1 = """
        SELECT max(listened_at) as max_listened_at
          FROM listen
         WHERE listened_at >= :least_accepted_dt
    """
    query2 = """
        SELECT max(listened_at) AS already_done_dt
             , max(created) AS already_max_created
          FROM listen_unique
    """
    with timescale.engine.connect() as connection:
        result = connection.execute(text(query1), {"least_accepted_dt": LISTEN_MINIMUM_DATE})
        row = result.fetchone()
        max_listened_at = row.max_listened_at

        result = connection.execute(text(query2))
        row = result.fetchone()
        already_done_dt = row.already_done_dt
        already_max_created = row.already_max_created

    if already_done_dt:
        already_done_chunk = (already_done_dt - LISTEN_MINIMUM_DATE) / CHUNK_SIZE
        chunk_remaining = (already_done_chunk - int(already_done_chunk)) * CHUNK_SIZE
        chunk_start = already_done_dt - chunk_remaining
    else:
        chunk_start = LISTEN_MINIMUM_DATE

    number_chunks = math.ceil((max_listened_at - chunk_start) / CHUNK_SIZE)
    chunk_count = 0
    start_time = time.monotonic()
    while chunk_start < max_listened_at:
        process_chunk(chunk_start)
        chunk_count += 1
        print_status_update(chunk_count, number_chunks, start_time)
        chunk_start += CHUNK_SIZE

    print("Finished chunkwise scan.")

    # since listens with older listened_at values can be inserted between runs, also do a scan with created field
    # to insert the remaining listens
    if already_max_created:
        # at MAX_CREATED_WHEN_ENABLED_ON_TEST, we enabled this migration for testing on test.lb
        # so new listens may have appeared since then. to ensure we don't miss any listens,
        # fixup from that date.
        already_max_created = min(already_max_created, MAX_CREATED_WHEN_ENABLED_ON_TEST)
    else:
        already_max_created = MAX_CREATED_WHEN_ENABLED_ON_TEST

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
