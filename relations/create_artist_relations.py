#!/usr/bin/env python3

from time import asctime
import psycopg2
from psycopg2.errors import OperationalError, DuplicateTable, UndefinedObject

import config
from utils import create_schema, dump_similarities, insert_artist_pairs

ARTIST_MBIDS_TO_EXCLUDE = [
    'f731ccc4-e22a-43af-a747-64213329e088',  # anonymous
    '125ec42a-7229-4250-afc5-e057484327fe',  # unknown
]


def create_or_truncate_table(conn):
    '''
    Create the artist_credit_relations table if it doesn't exist, otherwise truncate it.
    '''

    print(asctime(), "drop old indexes, truncate table or create new table")
    try:
        with conn.cursor() as curs:
            print(asctime(), "create table")
            curs.execute("""CREATE TABLE relations.artist_artist_relations (
                                         count integer,
                                         artist_0 integer,
                                         artist_1 integer)""")

    except DuplicateTable:
        conn.rollback()
        try:
            with conn.cursor() as curs:
                try:
                    curs.execute("TRUNCATE relations.artist_artist_relations")
                    conn.commit()
                except UndefinedObject:
                    conn.rollback()

                try:
                    curs.execute("DROP INDEX relations.artist_artist_relations_artist_0_ndx")
                    curs.execute("DROP INDEX relations.artist_artist_relations_artist_1_ndx")
                    conn.commit()
                except UndefinedObject:
                    conn.rollback()

        except OperationalError:
            print(asctime(), "failed to truncate existing table")
            conn.rollback()


def create_indexes(conn):
    '''
        Create the indexes for the completed relations tables
    '''

    print(asctime(), "creating indexes")
    try:
        with conn.cursor() as curs:
            curs.execute('''CREATE INDEX artist_artist_relations_artist_0_ndx
                                      ON relations.artist_artist_relations (artist_0)''')
            curs.execute('''CREATE INDEX artist_artist_relations_artist_1_ndx
                                      ON relations.artist_artist_relations (artist_1)''')
            conn.commit()
    except OperationalError:
        conn.rollback()
        print(asctime(), "creating indexes failed.")


def calculate_artist_similarities():

    relations = {}
    release_id = 0
    artists = []

    with psycopg2.connect(config.DB_CONNECT) as conn:
        create_schema(conn)
        with conn.cursor() as curs:
            count = 0
            print(asctime(), "query for various artist recordings")
            curs.execute("""SELECT DISTINCT r.id as release_id, a.id as artist_id, a.gid as artist_mbid
                                       FROM release r
                                       JOIN medium m ON m.release = r.id AND r.artist_credit = 1
                                       JOIN track t ON t.medium = m.id
                                       JOIN artist_credit ac ON t.artist_credit = ac.id
                                       JOIN artist_credit_name acm ON acm.artist_credit = ac.id
                                       JOIN artist a ON acm.artist = a.id""")
            print(asctime(), "load various artist recordings")
            while True:
                row = curs.fetchone()
                if not row:
                    break

                if row[2] in ARTIST_MBIDS_TO_EXCLUDE:
                    continue

                if release_id != row[0] and artists:
                    insert_artist_pairs(artists, relations)
                    artists = []

                artists.append(row[1])
                release_id = row[0]
                count += 1

        print(asctime(), "save relations to new table")
        create_or_truncate_table(conn)
        dump_similarities(conn, "relations.artist_artist_relations", relations)
        print(asctime(), "create indexes")
        create_indexes(conn)
        print(asctime(), "done!")


if __name__ == "__main__":
    calculate_artist_similarities()
