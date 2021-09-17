from operator import itemgetter

import psycopg2
from psycopg2.extras import execute_values
from listenbrainz.db import timescale
from listenbrainz import config

BATCH_SIZE = 10000

def load_artist_credit_index():
    with psycopg2.connect(config.MB_DATABASE_URI) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
            query = """SELECT artist_credit, array_agg(gid::TEXT) AS artist_mbids
                         FROM artist_credit_name acn
                         JOIN artist a
                           ON acn.artist = a.id
                     GROUP BY acn.artist_credit"""
            curs.execute(query)
            artist_credits = {}
            for row in curs.fetchall():
                artist_credits[row['artist_credit_id']] = row['artist_mbids']

    return artist_credits

                      
def insert_rows(updated_rows):

    conn = timescale.engine.raw_connection()
    with conn.cursor() as curs:
        try:
            query = """INSERT INTO tmp_listen_mbid_mapping (recording_msid, recording_mbid, release_mbid, artist_mbids,
                                   artist_credit_name, recording_name, match_type)
                            VALUES %s
                       ON CONFLICT DO NOTHING"""
            execute_values(curs, query, updated_rows, template=None)

        except psycopg2.OperationalError as err:
            app.logger.info( "Cannot insert MBID mapping rows. (%s)" % str(err))
            conn.rollback()
            return

        conn.commit()


def copy_rows_to_new_mbid_mapping():

    count = 0
    artist_credit_index = load_artist_credit_index()

    conn = timescale.engine.raw_connection()
    with conn.cursor() as curs:

        query = """SELECT * from listen_mbid_mapping"""
        curs.execute(query)

        updated_rows = []
        for row in curs.fetchall():
            updated_rows.append([ row['recording_msid'], row['recording_mbid'], row['release_mbid'], 
                artist_credit_name, row["recording_name"], row["match_type"] ]
            if len(rows) == BATCH_SIZE:
                count += len(updated_rows)
                insert_rows(updated_rows)
                updated_rows = []
                print("inserted %d rows" % count

        if updated_rows:
            insert_rows(updated_rows)

if __name__ == "__main__":
    load_artist_credit_index()
