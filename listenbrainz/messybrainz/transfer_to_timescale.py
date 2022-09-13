"""
Steps to move MsB to TS database.

    1. Create the destination tables and index. The index only exists to avoid duplicates which may happen
       when the script is run multiple times.
    2. Run the script for first time.
    3. Stop TS writer.
    4. Rerun the script to insert submissions since first run.
    5. Switch MsB submission to new tables by updating TS writer.
    6. Profit!
"""
import time
from typing import Optional

import psycopg2
import sqlalchemy.engine
from flask import current_app
from psycopg2.extras import execute_values
from sqlalchemy import text, create_engine
from sqlalchemy.pool import NullPool

from listenbrainz.db import timescale


msb_engine: Optional[sqlalchemy.engine.Engine] = None


def init_old_msb_db_connection(connect_str):
    global msb_engine
    while True:
        try:
            msb_engine = create_engine(connect_str, poolclass=NullPool)
            break
        except psycopg2.OperationalError as e:
            print("Couldn't establish connection to db: {}".format(str(e)))
            print("Sleeping for 2 seconds and trying again...")
            time.sleep(2)


def retrieve_data(last_row_id):
    query = """
            SELECT r.id
                 , r.gid AS recording_msid
                 , rj.data->>'title' AS recording
                 , rj.data->>'artist' AS artist
                 , rj.data->>'release' AS release
                 , rj.data->>'track_number' AS track_number
                 , r.submitted
              FROM recording r
              JOIN recording_json rj
                ON r.data = rj.id
             WHERE r.id > :last_row_id
          ORDER BY r.id ASC
        FETCH NEXT 50000 ROWS ONLY
    """
    with msb_engine.connect() as msb_conn:
        results = msb_conn.execute(text(query), last_row_id=last_row_id)
        return results.fetchall()


def insert_data(values):
    raw_conn = timescale.engine.raw_connection()
    query = """
        -- note that we are leaving out duration here, that is because it has not historically been a part of
        -- MsB so existing data in MsB will not have this field
        INSERT INTO messybrainz.submissions (gid, recording, artist_credit, release, track_number, submitted)
             VALUES %s
             ON CONFLICT (gid) DO NOTHING
    """
    with raw_conn.cursor() as curs:
        execute_values(curs, query, values)
    raw_conn.commit()


def retrieve_last_transferred_row_id():
    with timescale.engine.connect() as ts_conn:
        result = ts_conn.execute(text("""
            SELECT COALESCE(max(submitted), 'epoch'::timestamptz) AS latest
              FROM messybrainz.submissions
        """))
        row = result.fetchone()
    latest = row["latest"]
    current_app.logger.info("Latest submission row found: %s", latest.isoformat())

    with msb_engine.connect() as msb_conn:
        result = msb_conn.execute(text("""
            SELECT COALESCE(max(id), 0) AS last_row_id
              FROM recording
             WHERE submitted < :until
        """), until=latest)
        row = result.fetchone()

    row_id = row["last_row_id"]
    current_app.logger.info("Latest transferred row id: %d", row_id)
    return row_id


def run():
    """ Run the script to transfer data from MsB database to MsB schema in TS database.

    The script is safe to run multiple times. It looks for the latest submitted row in the destination
    table. It will then only transfer rows submitted to old db since that submission time. This assumes
    that no row has been written to the new table manually.
    """
    init_old_msb_db_connection(current_app.config['MESSYBRAINZ_SQLALCHEMY_DATABASE_URI'])
    current_app.logger.info("Starting MsB transfer.")
    last_row_id = retrieve_last_transferred_row_id()

    while True:
        results = retrieve_data(last_row_id)
        if not results:
            break

        processed = []
        for row in results:
            processed.append((
                row["recording_msid"],
                row["recording"],
                row["artist"],
                row["release"],
                row["track_number"],
                row["submitted"]
            ))
            last_row_id = row["id"]

        insert_data(processed)
        current_app.logger.info("Latest transferred row id: %d", last_row_id)

    current_app.logger.info("MsB Transfer Ended.")
