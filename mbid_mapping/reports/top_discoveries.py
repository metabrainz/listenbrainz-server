from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
from psycopg2.errors import OperationalError

from mapping.utils import insert_rows, log
import config

USERS_PER_BATCH = 100


def create_table(mb_conn):
    """ Create the top discoveries table in the mapping schema of a docker-musicbrinz
        instance. """

    try:
        with mb_conn.cursor() as curs:
            curs.execute("DROP TABLE IF EXISTS mapping.top_discoveries")
            curs.execute("""CREATE TABLE mapping.top_discoveries
                                       ( recording_mbid      UUID
                                       , recording_name      TEXT NOT NULL
                                       , artist_credit_name  TEXT NOT NULL
                                       , artist_mbids        UUID[] NOT NULL
                                       , listen_count        INTEGER NOT NULL
                                       , user_name           TEXT NOT NULL
                                       );""")
            mb_conn.commit()
    except (psycopg2.errors.OperationalError, psycopg2.errors.UndefinedTable) as err:
        log("mbid mapping: failed to create top discovery tables", err)
        mb_conn.rollback()
        raise


def create_indexes(mb_conn):
    """ Create the user_name index on the top discoveries table. """

    try:
        with mb_conn.cursor() as curs:
            curs.execute("""CREATE INDEX top_discoveries_ndx_user_name
                                      ON mapping.top_discoveries (user_name)""")
            mb_conn.commit()
    except (psycopg2.errors.OperationalError, psycopg2.errors.UndefinedTable) as err:
        log("mbid mapping: failed to create top discoveries indexes", err)
        mb_conn.rollback()
        raise


def fetch_user_list(lb_conn, year):
    """ Fetch the active users in the given year """

    with lb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as lb_curs:
        query = """SELECT DISTINCT user_name
                     FROM listen
                    WHERE listened_at >= %s
                      AND listened_at < %s"""

        start_ts = int(datetime(year, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp())
        end_ts = int(datetime(year + 1, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp())
        lb_curs.execute(query, (start_ts, end_ts))
        rows = lb_curs.fetchall()

    return [r[0] for r in rows]


def chunks(lst, n):
    """ Helper function to break a list into chunks """
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def fetch_top_discoveries_for_users(lb_conn, mb_conn, year):
    """ Actually fetch the top discoveries for the given year"""

    with lb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as lb_curs:
        with mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs:
            log("crate top_listens table")
            create_table(mb_conn)

            log("fetch active users")
            user_list = fetch_user_list(lb_conn, year)
            log("Process %d users." % len(user_list))

            # This query will select all listens/data for a given user list and create an array of the years when
            # a track was listened to. This data directly is not useful for anything directly, but from this 
            # a few types of playlists can be generated.
            query = """SELECT user_name
                            , data->>'track_name' AS track_name
                            , data->>'artist_name' AS artist_name
                            , array_agg(extract(year from to_timestamp(listened_at))::INT ORDER BY
                                        extract(year from to_timestamp(listened_at))::INT) AS years
                            , m.recording_mbid
                            , mm.artist_mbids
                         FROM listen l
              FULL OUTER JOIN mbid_mapping m
                           ON l.recording_msid = m.recording_msid
              FULL OUTER JOIN mbid_mapping_metadata mm
                              ON mm.recording_mbid = m.recording_mbid
                        WHERE user_name in %s
                          AND mm.recording_mbid IS NOT NULL
                     GROUP BY user_name, artist_name, mm.artist_mbids, track_name, m.recording_mbid
                       HAVING (array_agg(extract(year from to_timestamp(listened_at))::INT ORDER BY
                                         extract(year from to_timestamp(listened_at))::INT))[1] = %s
                     ORDER BY user_name, array_length(array_agg(extract(year from to_timestamp(listened_at))::INT), 1) DESC"""

            for users in chunks(user_list, USERS_PER_BATCH):
                log(users)
                lb_curs.execute(query, (tuple(users), year))

                top_recordings = []
                while True:
                    row = lb_curs.fetchone()
                    if not row:
                        break

                    if len(row["years"]) > 2:
                        top_recordings.append((row["recording_mbid"],
                                               row["track_name"],
                                               row["artist_name"],
                                               row["artist_mbids"],
                                               len(row["years"]),
                                               row["user_name"]))

                print("insert %d rows" % len(top_recordings))
                insert_rows(mb_curs, "mapping.top_discoveries", top_recordings)
                mb_conn.commit()


def calculate_top_discoveries(year):
    """
        Main entry point for creating top discoveries table.
    """

    with psycopg2.connect(config.SQLALCHEMY_TIMESCALE_URI) as lb_conn:
        with psycopg2.connect(config.MBID_MAPPING_DATABASE_URI) as mb_conn:
            create_table(mb_conn)
            fetch_top_discoveries_for_users(lb_conn, mb_conn, year)
            create_indexes(mb_conn)
