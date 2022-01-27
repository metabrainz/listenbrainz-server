from collections import defaultdict
import uuid

import psycopg2
from psycopg2.errors import OperationalError
from unidecode import unidecode
from mapping.utils import log, insert_rows

import config

LOOKAHEAD_STEPS = 5
BATCH_SIZE = 5000


def create_tables(mb_conn):
    """
        Create tables needed to create recording similarities. First
        is the temp table that the results will be stored in (in order
        to not conflict with the production version of this table).
        Second its format sort table to enables us to sort releases
        according to preferred format, release date and type.
    """

    # drop/create finished table
    try:
        with mb_conn.cursor() as curs:
            curs.execute("DROP TABLE IF EXISTS mapping.tmp_recording_similarity")
            curs.execute("""CREATE TABLE mapping.tmp_recording_similarity (
                                         mbid_0                    UUID NOT NULL,
                                         mbid_1                    UUID NOT NULL,
                                         similarity                REAL NOT NULL)""")
            mb_conn.commit()
    except (psycopg2.errors.OperationalError, psycopg2.errors.UndefinedTable) as err:
        log("recording_similarity: failed to create recording_similarity tables", err)
        mb_conn.rollback()
        raise


def create_indexes(conn):
    """
        Create indexes for the recording similarity tables
    """

    try:
        with conn.cursor() as curs:
            curs.execute("""CREATE INDEX tmp_recording_similarity_idx_mbid_0
                                      ON mapping.tmp_recording_similarity(mbid_0)""")
            curs.execute("""CREATE INDEX tmp_recording_similarity_idx_mbid_1
                                      ON mapping.tmp_recording_similarity(mbid_1)""")

        conn.commit()
    except OperationalError as err:
        log("recording_similarity: failed to create recording simiarlity indexes", err)
        conn.rollback()
        raise


def swap_table_and_indexes(conn):
    """
        Swap temp tables and indexes for production tables and indexes.
    """

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
            curs.execute("DROP TABLE IF EXISTS mapping.recording_similarity")
            curs.execute("""ALTER TABLE mapping.tmp_recording_similarity
                            RENAME TO recording_similarity""")

            curs.execute("""ALTER INDEX mapping.tmp_recording_similarity_idx_mbid_0
                            RENAME TO recording_similarity_idx_mbid_0""")
            curs.execute("""ALTER INDEX mapping.tmp_recording_similarity_idx_mbid_1
                            RENAME TO recording_similarity_idx_mbid_1""")
        conn.commit()
    except OperationalError as err:
        log("recording_similarity: failed to swap in new mbid mapping tables", str(err))
        conn.rollback()
        raise


def build_index(mb_conn, mb_curs, lb_conn, lb_curs):

    row_count = 0
    buffer = []
    recording_index = defaultdict(float)
    decrement = 1.0 / LOOKAHEAD_STEPS

    query = """    SELECT listened_at, user_name, mm.recording_mbid, m.artist_credit_id, m.artist_credit_name, m.recording_name
                     FROM listen
          FULL OUTER JOIN mbid_mapping mm
                       ON (data->'track_metadata'->'additional_info'->>'recording_msid')::uuid = mm.recording_msid
          FULL OUTER JOIN mbid_mapping_metadata m
                       ON mm.recording_mbid = m.recording_mbid
                    WHERE listened_at >= 1577836800
                 ORDER BY user_name, listened_at"""

#                    WHERE listened_at >= 1640995200

    log("execute query")
    lb_curs.execute(query)

    log("build index")
    while True:
        row = lb_curs.fetchone()
        if not row:
            break

        if row["recording_mbid"] is None:
            continue

        row_count += 1

        # If this is a different user, clear the buffer
        if len(buffer) > 0 and row["user_name"] != buffer[0]["user_name"]:
            buffer = []

        # append the row to the buffer
        buffer.append(row)
        if len(buffer) < LOOKAHEAD_STEPS + 1:
            continue

        mbid_0 = uuid.UUID(buffer[0]["recording_mbid"])
        value = 1.0
        # Now we have a full buffer with listens from one user
        for i in range(1, len(buffer)):
            mbid_1 = uuid.UUID(buffer[i]["recording_mbid"])

            # consider checking single artists in artist mbids -- could be an option!
            if mbid_0 != mbid_1 and buffer[0]["artist_credit_id"] != buffer[i]["artist_credit_id"]:
                # Check to make sure tracks are "close"
                if mbid_0 < mbid_1:
                    key = mbid_0.bytes + mbid_1.bytes
                else:
                    key = mbid_1.bytes + mbid_0.bytes
 
                recording_index[key] += value

            value -= decrement

        buffer.pop(0)

        if row_count % 1000000 == 0:
            log("processed %d rows" % row_count)


    log("Processing complete. Generated %d rows. Inserting results" % len(recording_index))
    create_tables(mb_conn)
    values = []
    inserted = 0
    for k, v in sorted(recording_index.items(), key=lambda item: item[1], reverse=True):
        mbid_0 = uuid.UUID(bytes=k[0:16])
        mbid_1 = uuid.UUID(bytes=k[16:32])
        values.append((str(mbid_0), str(mbid_1), v))

        if len(values) == BATCH_SIZE:
            insert_rows(mb_curs, "mapping.tmp_recording_similarity", values, cols=None)
            values = []
            inserted += BATCH_SIZE
            if inserted % 1000000 == 0:
                log("inserted %s rows" % inserted)

    if len(values) > 0:
        insert_rows(mb_curs, "mapping.tmp_recording_similarity", values, cols=None)

    log("Create indexes")
    create_indexes(mb_conn)
    log("Swap into production")
    swap_table_and_indexes(mb_conn)


def create_recording_similarity_index():
    """
    """

    with psycopg2.connect(config.MBID_MAPPING_DATABASE_URI) as mb_conn:
        with mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs:
            with psycopg2.connect(config.TIMESCALE_DATABASE_URI) as lb_conn:
                with lb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as lb_curs:
                    return build_index(mb_conn, mb_curs, lb_conn, lb_curs)
