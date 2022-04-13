from datetime import datetime
from itertools import combinations
import uuid
from collections import defaultdict
from struct import pack, unpack
from dataclasses import dataclass, field
from typing import Any


import psycopg2
import psycopg2.extras
from psycopg2.errors import OperationalError
from unidecode import unidecode
from mapping.utils import log, insert_rows

import config

BATCH_SIZE = 5000
MAX_SESSION_BREAK = 60 * 30  # 30 minutes
MAX_ITEMS_PER_SESSION = 50
AVG_SONG_LENGTH = 180  # 3 minutes
MIN_SIMILARITY_THRESHOLD = 10
DATA_START_YEAR = 2005
YEARS_PER_PASS = 3

def create_table(mb_conn, table):
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
            curs.execute(f"DROP TABLE IF EXISTS {table}")
            curs.execute(f"""CREATE TABLE {table} (
                                         mbid0                     UUID NOT NULL,
                                         mbid1                     UUID NOT NULL,
                                         similarity                INTEGER NOT NULL)""")
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


def index_buffer(artist_index, buffer):

    pairs = 0
    for i0, i1 in combinations(range(len(buffer)), 2):
        rec_mbid_0 = buffer[i0]["recording_mbid"]
        rec_mbid_1 = buffer[i1]["recording_mbid"]

        if rec_mbid_0 != rec_mbid_1 and buffer[i0]["artist_credit_id"] != buffer[i1]["artist_credit_id"]:
            for mbid_0 in buffer[i0]["artist_mbids"]:
                for mbid_1 in buffer[i1]["artist_mbids"]:
                    # We've now decided to insert this row, lets tightly encode it
                    if mbid_0 < mbid_1:
                        artist_index[mbid_0][mbid_1] += 1
                    else:
                        artist_index[mbid_1][mbid_0] += 1

                    pairs += 1

    return pairs


def build_partial_index(mb_conn, lb_conn, start_year, end_year):

    row_count = 0
    inserted = 0
    buffer = []
    artist_index = defaultdict(lambda: defaultdict(int))

    min_ts = datetime(year=start_year, month=1, day=1, hour=0, minute=0)
    max_ts = datetime(year=start_year, month=2, day=1, hour=0, minute=0)
#    max_ts = datetime(year=end_year+1, month=1, day=1, hour=0, minute=0)

    table_name = f"mapping.tmp_artist_similarity_{start_year}"
    create_table(mb_conn, table_name)
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

    with lb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as lb_curs:
        log("  execute partial index query")
        lb_curs.execute(query, (min_ts, max_ts))

        total_rows = lb_curs.rowcount

        log(f"  build partial index: {total_rows:,} rows")
        pairs = 0
        while True:
            row = lb_curs.fetchone()
            if not row:
                break

            if row["recording_mbid"] is None:
                continue

            row["artist_mbids"] = sorted(row["artist_mbids"]) #[1:-1].split(","))
            row_count += 1

            # If this is a different user or sufficient time has passed,
            # index the buffer and start a new session
            if len(buffer) and row["user_id"] != buffer[0]["user_id"]:
                save = True
            elif len(buffer) > MAX_ITEMS_PER_SESSION:
                save = True
            elif len(buffer) and row["listened_at"] - buffer[len(buffer) - 1]["listened_at"] + AVG_SONG_LENGTH > MAX_SESSION_BREAK:
                save = True
            else:
                save = False
            if save:
                if len(buffer) > 1:
                    pairs += index_buffer(artist_index, buffer)
                buffer = []

            # append the row to the buffer
            buffer.append(row)
            if row_count % 1000000 == 0:
                log("  indexed %d rows, %.1f%%" % (row_count, 100.0 * row_count / total_rows))

        with mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs:
            unique_pairs = 0
            rows = []
            for mbid0 in artist_index:
                unique_pairs += len(artist_index[mbid0])
                for mbid1 in artist_index[mbid0]:
                    rows.append((mbid0, mbid1, artist_index[mbid0][mbid1]))
                    if len(rows) >= BATCH_SIZE:
                        insert_rows(mb_curs, table_name, rows)
                        inserted += len(rows)
                        rows = []

            if rows:
                insert_rows(mb_curs, table_name, rows)
                inserted += len(rows)

    log(f"  inserted {inserted:,} unique pairs")

    return table_name


def build_final_index(mb_conn, lb_conn, tables):

    log("Create final index")
    total_rows = 0
    rows_processed = 0
    cursors = []
    for table in tables: 
        curs = mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(f"""SELECT mbid0::TEXT
                              , mbid1::TEXT
                              , similarity
                           FROM {table}
                       ORDER BY mbid0, mbid1""")
        total_rows += curs.rowcount
        cursors.append({"table":table, "curs": curs, "row": []})

    log("select queries executed, now processing results")
    create_table(mb_conn, "mapping.tmp_artist_similarity")
    with lb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as lb_curs:
        with mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs:

            mbid0 = None
            mbid1 = None
            similarity = 0
            inserted = 0
            batch_count = 0
            rows = []

            while True:
                # Load up rows for any cursor which is currently empty.
                # None indicates end of query, [] means new row should be fetched
                new_row_fetched = False
                for cur in cursors:
                    if cur["row"] is None or len(cur["row"]) > 0:
                        continue

                    cur["row"] = cur["curs"].fetchone()
                    if cur["row"] is not None:
                        new_row_fetched = True

                if not new_row_fetched:
                    break

                if mbid0 is None:
                    mbid = None
                    index = None
                    for i, cur in enumerate(cursors):
                        if cur["row"] is None:
                            continue

                        if mbid is None:
                            mbid = cur["row"]["mbid0"]
                            index = i

                        if cur["row"]["mbid0"] < mbid:
                            mbid = cur["row"]["mbid0"]
                            index = i

                    if index is None:
                        print("Could not find index, assuming all done.")
                        break

                    mbid0 = cursors[index]["row"]["mbid0"]
                    mbid1 = cursors[index]["row"]["mbid1"]
                    similarity = cursors[index]["row"]["similarity"]
                    cursors[index]["row"] = []
                    rows_processed += 1

                for cur in cursors:
                    if cur["row"] is None or len(cur["row"]) == 0:
                        continue
                    if cur["row"]["mbid0"] == mbid0 and cur["row"]["mbid1"] == mbid1:
                        similarity += cur["row"]["similarity"]
                        cur["row"] = []
                        break
                else:
                    if similarity > MIN_SIMILARITY_THRESHOLD:
                        rows.append((mbid0, mbid1, similarity))
                    mbid0 = None

                if len(rows) >= BATCH_SIZE:
                    insert_rows(mb_curs, "mapping.tmp_artist_similarity", rows)
                    lb_conn.commit()
                    rows = []
                    inserted += BATCH_SIZE
                    batch_count += 1
                    if batch_count % 10 == 0:
                        log("inserted %s rows, %.1f%%" % (inserted, 100.0 * rows_processed / total_rows))

            if len(rows) > 0:
                insert_rows(mb_curs, "mapping.tmp_artist_similarity", rows)
                lb_conn.commit()
                inserted += len(rows)

    log(f"Inserted {inserted:,} rows.")
    for cur in cursors:
        log(f"drop table {cur['table']}")
        cur["curs"].execute(f"DROP TABLE IF EXISTS {cur['table']}")
        mb_conn.commit()

    log("Create indexes")
    create_indexes(mb_conn)
    log("Swap into production")
    swap_table_and_indexes(mb_conn)


def create_artist_similarity_index():
    """
    """

    psycopg2.extras.register_uuid()
    current_year = datetime.now().year
    with psycopg2.connect(config.MBID_MAPPING_DATABASE_URI) as mb_conn:
        with psycopg2.connect(config.SQLALCHEMY_TIMESCALE_URI) as lb_conn:
            tables = []
            for year in range(DATA_START_YEAR, current_year + 2, YEARS_PER_PASS):
                log("Process %d -> %d" % (year, year + YEARS_PER_PASS - 1))
                tables.append(build_partial_index(mb_conn, lb_conn, year, year + YEARS_PER_PASS))

            build_final_index(mb_conn, lb_conn, tables)
