import re

import psycopg2
from psycopg2.errors import OperationalError
from unidecode import unidecode
import ujson

from mapping.utils import create_schema, insert_rows, log
from mapping.formats import create_formats_table
import config

BATCH_SIZE = 5000


def create_tables(mb_conn):
    """
        Create tables needed to create the MBID metadata cache. If old
        temp tables exist, drop them.
    """

    # drop/create finished table
    try:
        with mb_conn.cursor() as curs:
            curs.execute("DROP TABLE IF EXISTS mapping.tmp_mb_metadata_cache")
            curs.execute("""CREATE TABLE mapping.tmp_mb_metadata_cache (
                                         id                        SERIAL,
                                         recording_mbid            UUID NOT NULL,
                                         dirty                     BOOLEAN DEFAULT FALSE,
                                         data                      JSONB)""")
            mb_conn.commit()
    except (psycopg2.errors.OperationalError, psycopg2.errors.UndefinedTable) as err:
        log("mb metadata cache: failed to mb metadata cache tables", err)
        mb_conn.rollback()
        raise


def create_indexes(conn):
    """
        Create indexes for the cache
    """

    try:
        # TODO: Create GIN index on entity list 
        with conn.cursor() as curs:
            curs.execute("""CREATE UNIQUE INDEX tmp_mb_metadata_cache_idx_recording_mbid
                                      ON mapping.tmp_mb_metadata_cache(recording_mbid)""")
        conn.commit()
    except OperationalError as err:
        log("mb metadata cache: failed to mb metadata cache", err)
        conn.rollback()
        raise


def swap_table_and_indexes(conn):
    """
        Swap temp tables and indexes for production tables and indexes.
    """

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
            curs.execute("DROP TABLE IF EXISTS mapping.mb_metadata_cache")
            curs.execute("""ALTER TABLE mapping.tmp_mb_metadata_cache
                            RENAME TO mb_metadata_cache""")

            curs.execute("""ALTER INDEX mapping.tmp_mb_metadata_cache_idx_recording_mbid
                            RENAME TO mb_metadata_cache_idx_recording_mbid""")
        conn.commit()
    except OperationalError as err:
        log("mb metadata cache: failed to swap in new mb metadata cache tables", str(err))
        conn.rollback()
        raise

def create_json_blob(row):

    artist = {
        "begin_year": row["begin_date_year"],
        "end_year": row["end_date_year"],
        "type": row["type"],
        "gender": row["gender"],
        "area": row["area"],
        "relationships": "" }

    recording = {
        "length": row["length"],
    }

    return dict(row)


def create_mb_metadata_cache():
    """
        This function is the heart of the mb metadata cache. It fetches all the data for
        the cache in one go and then creates JSONB dicts for insertion into the cache.
    """

    query = """WITH artist_rels AS (
                            SELECT r.gid
                                 , array_agg(ARRAY[lt.name, url]) AS artist_links
                              FROM recording r
                              JOIN artist_credit ac
                                ON r.artist_credit = ac.id
                              JOIN artist_credit_name acn
                                ON acn.artist_credit = ac.id
                              JOIN artist a
                                ON acn.artist = a.id
                         FULL JOIN l_artist_url lau
                                ON lau.entity0 = a.id
                         FULL JOIN url u
                                ON lau.entity1 = u.id
                         FULL JOIN link l
                                ON lau.link = l.id
                         FULL JOIN link_type lt
                                ON l.link_type = lt.id
                             WHERE (lt.gid IN ('99429741-f3f6-484b-84f8-23af51991770'
                                              ,'fe33d22f-c3b0-4d68-bd53-a856badf2b15'
                                              ,'fe33d22f-c3b0-4d68-bd53-a856badf2b15'
                                              ,'689870a4-a1e4-4912-b17f-7b2664215698'
                                              ,'93883cf6-e818-4938-990e-75863f8db2d3'
                                              ,'6f77d54e-1d81-4e1a-9ea5-37947577151b'
                                              ,'e4d73442-3762-45a8-905c-401da65544ed'
                                              ,'611b1862-67af-4253-a64f-34adba305d1d'
                                              ,'f8319a2f-f824-4617-81c8-be6560b3b203'
                                              ,'34ae77fe-defb-43ea-95d4-63c7540bac78'
                                              ,'769085a1-c2f7-4c24-a532-2375a77693bd'
                                              ,'63cc5d1f-f096-4c94-a43f-ecb32ea94161'
                                              ,'6a540e5b-58c6-4192-b6ba-dbc71ec8fcf0')
                                    OR lt.gid IS NULL)
                          GROUP BY r.gid
               ), recording_rels AS (
                            SELECT r.gid
                                 , array_agg(ARRAY[lt.name, a1.name, a1.gid::TEXT, lat.name]) AS recording_links
                              FROM recording r
                              JOIN artist_credit ac
                                ON r.artist_credit = ac.id
                              JOIN artist_credit_name acn
                                ON acn.artist_credit = ac.id
                              JOIN artist a0
                                ON a0.id = acn.artist
                         FULL JOIN l_artist_recording lar
                                ON lar.entity1 = r.id
                              JOIN artist a1
                                ON lar.entity0 = a1.id
                         FULL JOIN link l
                                ON lar.link = l.id
                         FULL JOIN link_type lt
                                ON l.link_type = lt.id
                         FULL JOIN link_attribute la
                                ON la.link = l.id
                         FULL JOIN link_attribute_type lat
                                ON la.attribute_type = lat.id
                             WHERE (lt.gid IN ('628a9658-f54c-4142-b0c0-95f031b544da'
                                               ,'59054b12-01ac-43ee-a618-285fd397e461'
                                               ,'0fdbe3c6-7700-4a31-ae54-b53f06ae1cfa'
                                               ,'234670ce-5f22-4fd0-921b-ef1662695c5d'
                                               ,'3b6616c5-88ba-4341-b4ee-81ce1e6d7ebb'
                                               ,'92777657-504c-4acb-bd33-51a201bd57e1'
                                               ,'45d0cbc5-d65b-4e77-bdfd-8a75207cb5c5'
                                               ,'7e41ef12-a124-4324-afdb-fdbae687a89c'
                                               ,'b5f3058a-666c-406f-aafb-f9249fc7b122')
                                   OR lt.gid IS NULL)
                           GROUP BY r.gid
               )
                        SELECT a.name
                             , a.begin_date_year
                             , a.end_date_year
                             , at.name AS type
                             , ag.name AS gender
                             , ar.name AS area
                             , recording_links
                             , artist_links
                             , r.length
                             , r.gid as recording_mbid
                          FROM recording r
                          JOIN artist_credit ac
                            ON r.artist_credit = ac.id
                          JOIN artist_credit_name acn
                            ON acn.artist_credit = ac.id
                          JOIN artist a
                            ON acn.artist = a.id
                          JOIN artist_type  at
                            ON a.type = at.id
                          JOIN gender ag
                            ON a.type = ag.id
                     FULL JOIN area ar
                            ON a.area = ar.id
                     FULL JOIN artist_rels arl
                            ON arl.gid = r.gid
                     FULL JOIN recording_rels rrl
                            ON rrl.gid = r.gid"""


    query2 = """        SELECT a.name
                             , a.begin_date_year
                             , a.end_date_year
                             , at.name AS type
                             , ag.name AS gender
                             , ar.name AS area
                             , r.length
                             , r.gid as recording_mbid
                          FROM recording r
                          JOIN artist_credit ac
                            ON r.artist_credit = ac.id
                          JOIN artist_credit_name acn
                            ON acn.artist_credit = ac.id
                          JOIN artist a
                            ON acn.artist = a.id
                          JOIN artist_type  at
                            ON a.type = at.id
                          JOIN gender ag
                            ON a.type = ag.id
                     FULL JOIN area ar
                            ON a.area = ar.id
                         LIMIT 10"""

    log("mb metadata cache: start")
    with psycopg2.connect(config.MBID_MAPPING_DATABASE_URI) as mb_conn:
        with mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs:

            # Create the dest table (perhaps dropping the old one first)
            log("mb metadata cache: create schema")
            create_schema(mb_conn)

            log("mb metadata cache: drop old tables, create new tables")
            create_tables(mb_conn)

            with mb_conn.cursor() as mb_curs2:
                rows = []
                serial = 1
                log("mb metadata cache: fetch recordings")
                mb_curs.execute(query)
                total_rows = mb_curs.rowcount
                log(f"mb metadata cache: {total_rows} recordings in result")

                row_count = 0
                while True:
                    row = mb_curs.fetchone()
                    if not row:
                        break

                    data = create_json_blob(row)
                    rows.append((serial, row["recording_mbid"], "false", ujson.dumps(data)))
                    serial += 1

                    if len(rows) >= 10:
                        try:
                            insert_rows(mb_curs2, "mapping.tmp_mb_metadata_cache", rows)
                        except Exception:
                            print(rows)
                        mb_conn.commit()
                        rows = []

                        if serial % 1000000 == 0:
                            log("mb metadata cache: inserted %d rows. %.1f%%" % (serial, 100 * serial / total_rows))


                if rows:
                    insert_rows(mb_curs2, "mapping.tmp_mb_metadata_cache", rows)
                    mb_conn.commit()

            log("mb metadata cache: inserted %d rows total." % (serial - 1))
            log("mb metadata cache: create indexes")
            create_indexes(mb_conn)

            log("mb metadata cache: swap tables and indexes into production.")
            swap_table_and_indexes(mb_conn)

    log("mb metadata cache: done")
