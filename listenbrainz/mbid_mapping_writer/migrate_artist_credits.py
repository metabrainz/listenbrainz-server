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


def load_release_name_index():
    with psycopg2.connect(config.MB_DATABASE_URI) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
            query = """SELECT gid, name FROM release"""
            curs.execute(query)
            release_names = {}
            for row in curs.fetchall():
                release_name[row['gid']] = row['name']

    return release_names
                     

def insert_rows(mapping_rows, join_rows):

    conn = timescale.engine.raw_connection()
    with conn.cursor() as curs:
        try:
            query = """INSERT INTO tmp_listen_mbid_mapping (id, recording_mbid, release_mbid, release_name,
                                   artist_mbids, artist_credit_name, recording_name, match_type, last_updated)
                            VALUES %s
                       ON CONFLICT DO NOTHING"""
            execute_values(curs, query, mapping_rows, template=None)

            query = """INSERT INTO tmp_listen_join_listen_mbid_mapping (recording_msid, listen_mbid_mapping)
                            VALUES %s
                       ON CONFLICT DO NOTHING"""
            execute_values(curs, query, join_rows, template=None)

        except psycopg2.OperationalError as err:
            app.logger.info( "Cannot insert MBID mapping rows. (%s)" % str(err))
            conn.rollback()
            return

        conn.commit()


def copy_rows_to_new_mbid_mapping(app):

    count = 0

    app.logger.warning("Load artist credits")
    artist_credit_index = load_artist_credit_index()
    app.logger.warning("Load release names")
    release_name_index = load_name_index()

    conn = timescale.engine.raw_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:

        query = """SELECT * from listen_mbid_mapping limit 1000"""
        app.logger.warning("execute query")
        curs.execute(query)
        app.logger.warning("start migration")

        updated_rows = []
        join_rows = []
        id = 1
        while True:
            row = curs.fetchone()
            if not row:
                break

            if row["artist_credit_id"] is None or row["artist_credit_id"] not in artist_credit_index:
                updated_rows.append([ id, row['recording_mbid'], row['release_mbid'], 
                    None, None, None, None, 'no_match', row['last_updated'] ])
            else:
                updated_rows.append([ id, row['recording_mbid'], row['release_mbid'], 
                    release_name_index[row['release_mbid']], artist_credit_index[row["artist_credit_id"]],
                    row['artist_credit_name'], row["recording_name"], row["match_type"], row['last_updated'] ])

            join_rows.append([ row['recording_msid'], id ])

            id += 1

            if len(updated_rows) >= BATCH_SIZE:
                count += len(updated_rows)
                insert_rows(updated_rows, join_rows)
                updated_rows = []
                join_rows = []
                if count % 1000000 == 0:
                    app.logger.warning("inserted %d rows" % count)

        if updated_rows:
            insert_rows(updated_rows)

if __name__ == "__main__":
    app = create_app()
    copy_rows_to_new_mbid_mapping(app)
