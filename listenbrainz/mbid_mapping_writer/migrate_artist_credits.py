from operator import itemgetter

import psycopg2
from psycopg2.extras import execute_values
from listenbrainz.db import timescale
from listenbrainz import config
from listenbrainz.webserver import create_app

BATCH_SIZE = 10000

def load_artist_credit_index():
    with psycopg2.connect(config.MB_DATABASE_URI) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
            query = """SELECT artist_credit, array_agg(gid) AS artist_mbids
                         FROM artist_credit_name acn
                         JOIN artist a
                           ON acn.artist = a.id
                     GROUP BY acn.artist_credit"""
            curs.execute(query)
            artist_credits = {}
            for row in curs.fetchall():
                artist_credits[row['artist_credit']] = row['artist_mbids']

    return artist_credits

                      
def insert_rows(updated_rows):

    conn = timescale.engine.raw_connection()
    with conn.cursor() as curs:
        try:
            query = """INSERT INTO tmp_listen_mbid_mapping (recording_msid, recording_mbid, release_mbid, artist_mbids,
                                   artist_credit_name, recording_name, match_type, last_updated)
                            VALUES %s
                       ON CONFLICT DO NOTHING"""
            execute_values(curs, query, updated_rows, template=None)

        except psycopg2.OperationalError as err:
            app.logger.info( "Cannot insert MBID mapping rows. (%s)" % str(err))
            conn.rollback()
            return

        conn.commit()


def copy_rows_to_new_mbid_mapping(app):

    count = 0

    app.logger.warning("Load artist credits")
    artist_credit_index = load_artist_credit_index()

    conn = timescale.engine.raw_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:

        query = """SELECT * from listen_mbid_mapping"""
        app.logger.warning("execute query")
        curs.execute(query)
        app.logger.warning("start migration")

        updated_rows = []
        while True:
            row = curs.fetchone()
            if not row:
                break

            if row["artist_credit_id"] is None or row["artist_credit_id"] not in artist_credit_index:
                updated_rows.append([ row['recording_msid'], row['recording_mbid'], row['release_mbid'], 
                    None, None, None, 'no_match', row['last_updated'] ])
            else:
                updated_rows.append([ row['recording_msid'], row['recording_mbid'], row['release_mbid'], 
                    artist_credit_index[row["artist_credit_id"]],
                    row['artist_credit_name'], row["recording_name"], row["match_type"], row['last_updated'] ])

            if len(updated_rows) >= BATCH_SIZE:
                count += len(updated_rows)
                insert_rows(updated_rows)
                updated_rows = []
                if count % 1000000 == 0:
                    app.logger.warning("inserted %d rows" % count)

        if updated_rows:
            insert_rows(updated_rows)

if __name__ == "__main__":
    app = create_app()
    copy_rows_to_new_mbid_mapping(app)
