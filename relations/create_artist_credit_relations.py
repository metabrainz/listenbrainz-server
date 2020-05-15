#!/usr/bin/env python3

from time import asctime
import psycopg2
from psycopg2.errors import OperationalError, DuplicateTable, UndefinedObject

import config
from utils import create_schema, dump_similarities, insert_artist_pairs

ARTIST_CREDIT_IDS_TO_EXCLUDE = [
    15071,  # anonymous
    97546,  # unknown
]


def create_or_truncate_table(conn):
    '''
        Create the artist_credit_relations table if it doesn't exist, otherwise truncate it.
    '''

    print(asctime(), "drop old indexes, truncate table or create new table")
    try:
        with conn.cursor() as curs:
            print(asctime(), "create table")
            curs.execute("""CREATE TABLE relations.artist_credit_artist_credit_relations (
                                         count integer,
                                         artist_credit_0 integer,
                                         artist_credit_1 integer)""")

    except DuplicateTable:
        conn.rollback()
        try:
            with conn.cursor() as curs:
                try:
                    curs.execute("TRUNCATE relations.artist_credit_artist_credit_relations")
                    conn.commit()
                except UndefinedObject:
                    conn.rollback()

                try:
                    curs.execute("DROP INDEX relations.artist_credit_artist_credit_relations_artist_0_ndx")
                    curs.execute("DROP INDEX relations.artist_credit_artist_credit_relations_artist_1_ndx")
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
            curs.execute('''CREATE INDEX artist_credit_artist_credit_relations_artist_0_ndx
                                      ON relations.artist_credit_artist_credit_relations (artist_credit_0)''')
            curs.execute('''CREATE INDEX artist_credit_artist_credit_relations_artist_1_ndx
                                      ON relations.artist_credit_artist_credit_relations (artist_credit_1)''')
            conn.commit()
    except OperationalError:
        conn.rollback()
        print(asctime(), "creating indexes failed.")


def calculate_artist_credit_similarities():
    '''
        Calculate artist credit relations by fetching recordings for various artist albums and then
        using the fact that two artists are on teh same album as a vote that they are related.
    '''

    relations = {}
    release_id = 0
    artist_credits = []

    with psycopg2.connect(config.DB_CONNECT) as conn:
        create_schema(conn)
        with conn.cursor() as curs:
            count = 0
            print(asctime(), "query for various artist recordings")
            curs.execute("""SELECT DISTINCT r.id as release_id, ac.id as artist_id
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

                if row[1] in ARTIST_CREDIT_IDS_TO_EXCLUDE:
                    continue

                if release_id != row[0] and artist_credits:
                    insert_artist_pairs(artist_credits, relations)
                    artist_credits = []

                artist_credits.append(row[1])
                release_id = row[0]
                count += 1

        print(asctime(), "save relations to new table")
        create_or_truncate_table(conn)
        dump_similarities(conn, "relations.artist_credit_artist_credit_relations", relations)
        print(asctime(), "create indexes")
        create_indexes(conn)
        print(asctime(), "done!")


if __name__ == "__main__":
    calculate_artist_credit_similarities()
