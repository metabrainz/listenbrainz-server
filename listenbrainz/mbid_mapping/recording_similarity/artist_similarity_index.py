from datetime import datetime
from itertools import combinations
import uuid
from collections import defaultdict
from struct import pack, unpack
from dataclasses import dataclass, field
from typing import Any


import psycopg2
from psycopg2.errors import OperationalError
from unidecode import unidecode
from mapping.utils import log, insert_rows

import config

BATCH_SIZE = 5000
MAX_SESSION_DURATION = 60 * 60 * 2  # 2 hours
MIN_SIMILARITY_THRESHOLD = 100

def create_tables(mb_conn):
    """
        Create tables needed to create artist similarities. First
        is the temp table that the results will be stored in (in order
        to not conflict with the production version of this table).
        Second its format sort table to enables us to sort releases
        according to preferred format, release date and type.
    """

    # drop/create finished table
    try:
        with mb_conn.cursor() as curs:
            curs.execute("DROP TABLE IF EXISTS mapping.tmp_artist_similarity")
            curs.execute("""CREATE TABLE mapping.tmp_artist_similarity (
                                         mbid0                     UUID NOT NULL,
                                         mbid1                     UUID NOT NULL,
                                         similarity                REAL NOT NULL)""")
            mb_conn.commit()
    except (psycopg2.errors.OperationalError, psycopg2.errors.UndefinedTable) as err:
        log("artist_similarity: failed to create artist_similarity tables", err)
        mb_conn.rollback()
        raise


def create_indexes(conn):
    """
        Create indexes for the recording similarity tables
    """

    try:
        with conn.cursor() as curs:
            curs.execute("""CREATE INDEX tmp_artist_similarity_idx_mbid0
                                      ON mapping.tmp_artist_similarity(mbid0)""")
            curs.execute("""CREATE INDEX tmp_artist_similarity_idx_mbid1
                                      ON mapping.tmp_artist_similarity(mbid1)""")

        conn.commit()
    except OperationalError as err:
        log("artist_similarity: failed to create recording simiarlity indexes", err)
        conn.rollback()
        raise


def swap_table_and_indexes(conn):
    """
        Swap temp tables and indexes for production tables and indexes.
    """

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
            curs.execute("DROP TABLE IF EXISTS mapping.artist_similarity")
            curs.execute("""ALTER TABLE mapping.tmp_artist_similarity
                            RENAME TO artist_similarity""")

            curs.execute("""ALTER INDEX mapping.tmp_artist_similarity_idx_mbid0
                            RENAME TO artist_similarity_idx_mbid0""")
            curs.execute("""ALTER INDEX mapping.tmp_artist_similarity_idx_mbid1
                            RENAME TO artist_similarity_idx_mbid1""")
        conn.commit()
    except OperationalError as err:
        log("artist_similarity: failed to swap in new mbid mapping tables", str(err))
        conn.rollback()
        raise

def get_mbid_offset(mbid_index, inverse_mbid_index, mbid):
    try:
        return mbid_index[mbid.bytes]
    except KeyError:
        offset = len(mbid_index)
        mbid_index[mbid.bytes] = offset
        inverse_mbid_index[offset] = mbid.bytes
        return offset

def index_buffer(artist_index, mbid_index, inverse_mbid_index, buffer):

    pairs = 0
    for i0, i1 in combinations(range(len(buffer)), 2):
        rec_mbid_0 = uuid.UUID(buffer[i0]["recording_mbid"])
        rec_mbid_1 = uuid.UUID(buffer[i1]["recording_mbid"])

        if rec_mbid_0 != rec_mbid_1 and buffer[i0]["artist_credit_id"] != buffer[i1]["artist_credit_id"]:
            for mbid_0 in buffer[i0]["artist_mbids"]:
                mbid_0 = uuid.UUID(mbid_0)
                for mbid_1 in buffer[i1]["artist_mbids"]:
                    mbid_1 = uuid.UUID(mbid_1)

                    # We've now decided to insert this row, lets tightly encode it
                    mbid_0_offset = get_mbid_offset(mbid_index, inverse_mbid_index, mbid_0)
                    mbid_1_offset = get_mbid_offset(mbid_index, inverse_mbid_index, mbid_1)
                    if mbid_0 < mbid_1:
                        artist_index[mbid_0_offset][mbid_1_offset] += 1
                    else:
                        artist_index[mbid_1_offset][mbid_0_offset] += 1

                    pairs += 1

    return pairs


def build_index(mb_conn, mb_curs, lb_conn, lb_curs):

    row_count = 0
    buffer = []
    mbid_index = {}
    inverse_mbid_index = {}
    artist_index = defaultdict(lambda: defaultdict(float))

    min_ts = datetime(year=2010, month=1, day=1, hour=0, minute=0)
    max_ts = datetime(year=2015, month=1, day=1, hour=0, minute=0)
    query = """    SELECT listened_at
                        , user_id
                        , mm.recording_mbid
                        , m.artist_mbids
                        , m.artist_credit_id
                        , m.artist_credit_name
                        , m.recording_name
                     FROM listen
          FULL OUTER JOIN mbid_mapping mm
                       ON (data->'track_metadata'->'additional_info'->>'recording_msid')::uuid = mm.recording_msid
          FULL OUTER JOIN mbid_mapping_metadata m
                       ON mm.recording_mbid = m.recording_mbid
                    WHERE created >= %s
                      AND created <= %s
                 ORDER BY user_id, listened_at, mm.recording_mbid"""

    log("execute query")
    lb_curs.execute(query, (min_ts, max_ts))

    total_rows = lb_curs.rowcount

    log(f"build index: {total_rows:,} rows")
    pairs = 0
    session_start = 0
    while True:
        row = lb_curs.fetchone()
        if not row:
            break

        if row["recording_mbid"] is None:
            continue

        row["artist_mbids"] = sorted(row["artist_mbids"][1:-1].split(","))
        row_count += 1

        # If this is a different user or sufficient time has passed,
        # index the buffer and start a new session
        if (len(buffer) > 0 and row["user_id"] != buffer[0]["user_id"]) or \
            (session_start is not None and row["listened_at"] - session_start >= MAX_SESSION_DURATION):
            if len(buffer) > 1:
                pairs += index_buffer(artist_index, mbid_index, inverse_mbid_index, buffer)

            buffer = []
            session_start = None

        if session_start is None:
            session_start = row["listened_at"]

        # append the row to the buffer
        buffer.append(row)
        if row_count % 1000000 == 0:
            log("indexed %d rows, %.1f%%" % (row_count, 100.0 * row_count / total_rows))

    unique_pairs = 0
    for mbid0 in artist_index:
        unique_pairs += len(artist_index[mbid0])


    log(f"Indexing complete. Generated {unique_pairs:,} unique pairs from {pairs:,} pairs. Inserting results")

    create_tables(mb_conn)
    values = []
    inserted = 0
    for mbid_0_offset in artist_index:
        mbid_0 = uuid.UUID(bytes=inverse_mbid_index[mbid_0_offset])
        for mbid_1_offset in artist_index[mbid_0_offset]:
            mbid_1 = uuid.UUID(bytes=inverse_mbid_index[mbid_1_offset])

            sim = artist_index[mbid_0_offset][mbid_1_offset]
            if sim > MIN_SIMILARITY_THRESHOLD:
                values.append((str(mbid_0), str(mbid_1), sim))
            else:
                unique_pairs -= 1

            if len(values) == BATCH_SIZE:
                insert_rows(mb_curs, "mapping.tmp_artist_similarity", values, cols=None)
                values = []
                inserted += BATCH_SIZE
                if inserted % 1000000 == 0:
                    log("inserted %s rows, %.1f%%" % (inserted, 100.0 * inserted / unique_pairs))

    if len(values) > 0:
        insert_rows(mb_curs, "mapping.tmp_artist_similarity", values, cols=None)
        inserted += len(values)
        values = []

    # Free up space immediately
    mbid_index = None
    artist_index = None
    inverse_mbid_index = None

    log(f"Inserted {inserted:,} rows.")

    log("Create indexes")
    create_indexes(mb_conn)
    log("Swap into production")
    swap_table_and_indexes(mb_conn)


def create_artist_similarity_index():
    """
    """

    with psycopg2.connect(config.MBID_MAPPING_DATABASE_URI) as mb_conn:
        with mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs:
            with psycopg2.connect(config.TIMESCALE_DATABASE_URI) as lb_conn:
                with lb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as lb_curs:
                    return build_index(mb_conn, mb_curs, lb_conn, lb_curs)
