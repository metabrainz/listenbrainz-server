from time import asctime
import psycopg2


def create_schema(conn):
    '''
        Create the relations schema if it doesn't already exist
    '''

    try:
        with conn.cursor() as curs:
            print(asctime(), "create schema")
            curs.execute("CREATE SCHEMA IF NOT EXISTS relations")
            conn.commit()
    except OperationalError:
        print(asctime(), "failed to create schema 'relations'")
        conn.rollback()

        print(asctime(), "creating indexes failed.")


def insert_artist_pairs(artist_pairs, relations):
    '''
        After the artist(_credit) pairs have been collected, create the list of relations for this artist.
    '''

    for a0 in artist_pairs:
        for a1 in artist_pairs:
            if a0 == 1 or a1 == 1:
                continue

            if a0 == a1:
                continue

            if a0 < a1:
                k = "%d=%d" % (a0, a1)
            else:
                k = "%d=%d" % (a1, a0)

            try:
                relations[k][0] += 1
            except KeyError:
                relations[k] = [1, a0, a1]


def insert_rows(curs, table, values):
    '''
        Use the bulk insert function to insert rows into the relations table.
    '''

    query = ("INSERT INTO %s VALUES " % table) + ",".join(values)
    try:
        curs.execute(query)
    except psycopg2.OperationalError:
        print(asctime(), "failed to insert rows")


def dump_similarities(conn, table, relations):
    '''
        After all the similarities have been collected, write then to the DB in batches.
    '''

    print(asctime(), "write relations to table")

    values = []
    with conn.cursor() as curs:

        for k in relations:
            r = relations[k]
            if r[0] > 2:
                values.append("(%d, %d, %d)" % (r[0], r[1], r[2]))

            if len(values) > 1000:
                insert_rows(curs, table, values)
                conn.commit()
                values = []

        if len(values) > 0:
            insert_rows(curs, table, values)
            conn.commit()
