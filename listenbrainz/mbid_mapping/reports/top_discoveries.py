import psycopg2
import psycopg2.extras
from psycopg2.errors import OperationalError

from mapping.utils import insert_rows, log
import config

NUM_DISCOVERIES_PER_USER = 25

#    with psycopg2.connect(config.MBID_MAPPING_DATABASE_URI) as mb_conn:
#    with psycopg2.connect(config.SQLALCHEMY_DATABASE_URI) as lb_conn:


def create_table(mb_conn):
    try:
        with mb_conn.cursor() as curs:
            curs.execute("DROP TABLE IF EXISTS mapping.top_discoveries_2021")
            curs.execute("""CREATE TABLE mapping.top_discoveries_2021
                                       ( recording_msid     UUID NOT NULL
                                       , recording_mbid     UUID
                                       , recording_name     TEXT NOT NULL
                                       , artist_credit_name TEXT NOT NULL
                                       , listen_count       INTEGER NOT NULL
                                       , user_name          TEXT NOT NULL
                                       );""")
            mb_conn.commit()
    except (psycopg2.errors.OperationalError, psycopg2.errors.UndefinedTable) as err:
        log("mbid mapping: failed to create top discovery tables", err)
        mb_conn.rollback()
        raise

def create_indexes(mb_conn):
    try:
        with mb_conn.cursor() as curs:
            curs.execute("""CREATE INDEX top_discoveries_2021_ndx_user_name
                                      ON mapping.top_discoveries_2021 (user_name)""")
            mb_conn.commit()
    except (psycopg2.errors.OperationalError, psycopg2.errors.UndefinedTable) as err:
        log("mbid mapping: failed to create top discoveries indexes", err)
        mb_conn.rollback()
        raise


def fetch_top_discoveries_for_users(lb_conn, mb_conn, year, users):

    with lb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as lb_curs:
        with mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs:
            create_table(mb_conn)

            query = """SELECT user_name
                            , track_name
                            , data->'track_metadata'->>'artist_name' AS artist_name
                            , data->'track_metadata'->'additional_info'->>'recording_msid'::TEXT AS rec_msid
                            , array_agg(extract(year from to_timestamp(listened_at))::INT ORDER BY 
                                        extract(year from to_timestamp(listened_at))::INT) AS years
                            , recording_mbid
                         FROM listen
              FULL OUTER JOIN listen_join_listen_mbid_mapping lj
                           ON (data->'track_metadata'->'additional_info'->>'recording_msid')::uuid = lj.recording_msid
              FULL OUTER JOIN listen_mbid_mapping m
                              ON lj.listen_mbid_mapping = m.id
                        WHERE user_name in %s
                     GROUP BY user_name, rec_msid, recording_mbid, artist_name, track_name
                       HAVING (array_agg(extract(year from to_timestamp(listened_at))::INT ORDER BY
                                         extract(year from to_timestamp(listened_at))::INT))[1] = %s
                     ORDER BY user_name, array_length(array_agg(extract(year from to_timestamp(listened_at))::INT), 1) DESC"""

            lb_curs.execute(query, (tuple(users), year))

            top_recordings = []
            while True:
                row = lb_curs.fetchone()
                if not row:
                    break

                if len(row["years"]) > 2:
                    top_recordings.append((row["rec_msid"],
                                           row["recording_mbid"],
                                           row["track_name"],
                                           row["artist_name"],
                                           len(row["years"]),
                                           row["user_name"]))

            print("insert %d rows for users %s" % (len(top_recordings), str(users)))
            insert_rows(mb_curs, "mapping.top_discoveries_2021", top_recordings)
            mb_conn.commit()



def get_top_discoveries(year):
    """
    """

    with psycopg2.connect(config.TIMESCALE_DATABASE_URI) as lb_conn:
        with psycopg2.connect(config.MBID_MAPPING_DATABASE_URI) as mb_conn:
            create_table(mb_conn)
            fetch_top_discoveries_for_users(lb_conn, mb_conn, year, ["rob", "mr_monkey"])
            create_indexes(mb_conn)


get_top_discoveries(2021)
