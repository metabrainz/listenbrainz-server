from datetime import datetime, timezone

import click
import psycopg2
import psycopg2.extras
from psycopg2.errors import OperationalError

from mapping.utils import insert_rows, log
import config

BATCH_SIZE = 5000


def create_table(mb_conn):
    """ Create the tracks of the year table in the mapping schema of a docker-musicbrinz
        instance. """

    try:
        with mb_conn.cursor() as curs:
            curs.execute("DROP TABLE IF EXISTS mapping.tracks_of_the_year")
            curs.execute("""CREATE TABLE mapping.tracks_of_the_year
                                       ( user_name          TEXT NOT NULL
                                       , recording_mbid     UUID NOT NULL
                                       , recording_name     TEXT NOT NULL
                                       , artist_credit_name TEXT NOT NULL
                                       , artist_mbids       UUID[] NOT NULL
                                       , listen_count       INTEGER NOT NULL
                                       )""")
            mb_conn.commit()
    except (psycopg2.errors.OperationalError, psycopg2.errors.UndefinedTable) as err:
        log("mbid mapping: failed to create tracks of the year table", err)
        mb_conn.rollback()
        raise


def create_indexes(mb_conn):
    """ Create the user_name index on the tracks of the year table. """

    try:
        with mb_conn.cursor() as curs:
            curs.execute("""CREATE INDEX tracks_of_the_year_ndx_user_name
                                      ON mapping.tracks_of_the_year (user_name)""")
            mb_conn.commit()
    except (psycopg2.errors.OperationalError, psycopg2.errors.UndefinedTable) as err:
        log("mbid mapping: failed to create tracks of the year indexes", err)
        mb_conn.rollback()
        raise


def fetch_user_list(mb_conn, year):
    """ Fetch the distinct list of users from tracks listened table """

    with mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs:
        query = """SELECT DISTINCT user_name
                     FROM mapping.tracks_of_the_year"""
        mb_curs.execute(query)
        rows = mb_curs.fetchall()

    return [r[0] for r in rows]


def chunks(lst, n):
    """ Helper function to break a list into chunks """
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def fetch_tracks_listened_to(lb_conn, mb_conn, start_ts, end_ts):
    """ Actually fetch the top discoveries for the given year and set of users """

    with lb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as lb_curs:
        with mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs:
            log("create tracks listened table")
            create_table(mb_conn)

            log("fetch tracks listened to")
            # Fetch the basic data for all tracks that users listened to in a given year.
            query = """SELECT user_name
                            , m.recording_mbid
                            , md.recording_name
                            , md.artist_credit_name
                            , md.artist_mbids
                            , count(*) AS listen_count
                         FROM listen l
                         JOIN mbid_mapping m
                           ON l.recording_msid = m.recording_msid
                         JOIN mbid_mapping_metadata md
                           ON m.recording_mbid = md.recording_mbid
                        WHERE listened_at >= %s
                          AND listened_at < %s
                          AND m.recording_mbid is not null
                     GROUP BY m.recording_mbid, md.recording_name,
                              md.artist_credit_name, md.artist_mbids, user_name""" % (start_ts, end_ts)

            to_insert = []
            lb_curs.execute(query)
            while True:
                row = lb_curs.fetchone()
                if not row:
                    break

                to_insert.append(row)
                if len(to_insert) >= BATCH_SIZE:
                    insert_rows(mb_curs, "mapping.tracks_of_the_year", to_insert)
                    to_insert = []
                    mb_conn.commit()

            insert_rows(mb_curs, "mapping.tracks_of_the_year", to_insert)
            mb_conn.commit()


def calculate_tracks_of_the_year(year):
    """
        Main entry point for creating top discoveries table.
    """

    start_ts = int(datetime(year=year, month=1, day=1, tzinfo=timezone.utc).timestamp())
    end_ts = int(datetime(year=year + 1, month=1, day=1, tzinfo=timezone.utc).timestamp())
    with psycopg2.connect(config.SQLALCHEMY_TIMESCALE_URI) as lb_conn:
        with psycopg2.connect(config.MBID_MAPPING_DATABASE_URI) as mb_conn:
            create_table(mb_conn)
            fetch_tracks_listened_to(lb_conn, mb_conn, start_ts, end_ts)
            create_indexes(mb_conn)
