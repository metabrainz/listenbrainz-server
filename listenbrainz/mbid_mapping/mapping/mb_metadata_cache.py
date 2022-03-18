import re

import psycopg2
from psycopg2.errors import OperationalError
from unidecode import unidecode
import ujson
import json
import uuid
import psycopg2.extras

from mapping.utils import create_schema, insert_rows, log
from mapping.formats import create_formats_table
import config

BATCH_SIZE = 5000


def create_tables(lb_conn):
    """
        Create tables needed to create the MBID metadata cache. If old
        temp tables exist, drop them.
    """

    # drop/create finished table
    try:
        with lb_conn.cursor() as curs:
            curs.execute("DROP TABLE IF EXISTS tmp_mb_metadata_cache")
            curs.execute("""CREATE TABLE tmp_mb_metadata_cache (
                                         id                        SERIAL
                                       , recording_mbid            UUID NOT NULL
                                       , dirty                     BOOLEAN DEFAULT FALSE
                                       , artist_mbids              UUID[] NOT NULL
                                       , recording_data            JSONB NOT NULL
                                       , artist_data               JSONB NOT NULL
                                       , tag_data                  JSONB NOT NULL)""")
            lb_conn.commit()
    except (psycopg2.errors.OperationalError, psycopg2.errors.UndefinedTable) as err:
        log("mb metadata cache: failed to mb metadata cache tables", err)
        lb_conn.rollback()
        raise


def create_indexes(conn):
    """
        Create indexes for the cache
    """

    try:
        # TODO: Create GIN index on entity list 
        with conn.cursor() as curs:
            curs.execute("""CREATE UNIQUE INDEX tmp_mb_metadata_cache_idx_recording_mbid
                                      ON tmp_mb_metadata_cache(recording_mbid)""")
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
            curs.execute("DROP TABLE IF EXISTS mb_metadata_cache")
            curs.execute("""ALTER TABLE tmp_mb_metadata_cache
                            RENAME TO mb_metadata_cache""")

            curs.execute("""ALTER INDEX tmp_mb_metadata_cache_idx_recording_mbid
                            RENAME TO mb_metadata_cache_idx_recording_mbid""")
        conn.commit()
    except OperationalError as err:
        log("mb metadata cache: failed to swap in new mb metadata cache tables", str(err))
        conn.rollback()
        raise


def create_json_data(row):
    """ Format the data returned into sane JSONB blobs for easy consumption. Return
        recording_data, artist_data, tag_data JSON strings as a tuple.
    """

    artists = []
    artist_mbids = []

    for mbid, begin_year, end_year, artist_type, gender, area, rels in row["artist_data"]:
        data = { }
        if begin_year is not None:
            data["begin_year"] = begin_year
        if end_year is not None:
            data["end_year"] = end_year
        if artist_type is not None:
            data["type"] = artist_type
        if area is not None:
            data["area"] = area
        if rels:
            filtered = {}
            for name, url in rels:
                if name is None or url is None:
                    continue
                filtered[name] = url
            if filtered:
                data["rels"] = filtered
        if artist_type == "Person":
            data["gender"] = gender
        artists.append(data)
        artist_mbids.append(uuid.UUID(mbid))

    recording_rels = []
    for rel_type, artist_name, artist_mbid, instrument in row["recording_links"] or []:
        recording_rels.append({"type": rel_type,
                                "artist_name": artist_name,
                                "artist_mbid": artist_mbid,
                                "instrument": instrument})
        artist_mbids.append(uuid.UUID(artist_mbid))

    recording_tags = []
    for tag, count, genre_mbid in row["recording_tags"] or []:
        tag = { "tag": tag, "count": count }
        if genre_mbid is not None:
           tag["genre_mbid"] = genre_mbid
        recording_tags.append(tag)

    artist_tags = []
    for tag, count, artist_mbid, genre_mbid in row["artist_tags"] or []:
        tag = { "tag": tag,
                "count": count,
                "artist_mbid": artist_mbid }
        if genre_mbid is not None:
           tag["genre_mbid"] = genre_mbid
        artist_tags.append(tag)

    return (artist_mbids,
            ujson.dumps({ "rels" : recording_rels}),
            ujson.dumps(artists),
            ujson.dumps({ "recording": recording_tags, "artist": artist_tags }))


def create_cache(mb_conn, mb_curs, lb_conn, lb_curs):
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
                         LEFT JOIN l_artist_url lau
                                ON lau.entity0 = a.id
                         LEFT JOIN url u
                                ON lau.entity1 = u.id
                         LEFT JOIN link l
                                ON lau.link = l.id
                         LEFT JOIN link_type lt
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
--AND r.gid in ('e97f805a-ab48-4c52-855e-07049142113d')
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
                         LEFT JOIN l_artist_recording lar
                                ON lar.entity1 = r.id
                              JOIN artist a1
                                ON lar.entity0 = a1.id
                         LEFT JOIN link l
                                ON lar.link = l.id
                         LEFT JOIN link_type lt
                                ON l.link_type = lt.id
                         LEFT JOIN link_attribute la
                                ON la.link = l.id
                         LEFT JOIN link_attribute_type lat
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
--AND r.gid in ('e97f805a-ab48-4c52-855e-07049142113d')
                           GROUP BY r.gid
               ), artist_data AS (
                        SELECT r.gid
                             , array_agg(jsonb_build_array(a.gid
                                                          ,a.begin_date_year
                                                          ,a.end_date_year
                                                          ,at.name
                                                          ,ag.name
                                                          ,ar.name
                                                          ,artist_links)) AS artist_data
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
                     LEFT JOIN area ar
                            ON a.area = ar.id
                     LEFT JOIN artist_rels arl
                            ON arl.gid = r.gid
--WHERE r.gid in ('e97f805a-ab48-4c52-855e-07049142113d')
                      GROUP BY r.gid
               ), recording_tags AS (
                        SELECT r.gid AS recording_mbid
                             , array_agg(jsonb_build_array(t.name, count, g.gid)) AS recording_tags
                          FROM musicbrainz.tag t
                          JOIN recording_tag rt
                            ON rt.tag = t.id
                          JOIN recording r
                            ON rt.recording = r.id
                     LEFT JOIN genre g
                            ON t.name = g.name
                         WHERE count > 0
--AND r.gid in ('e97f805a-ab48-4c52-855e-07049142113d')
                         GROUP BY r.gid
               ), artist_tags AS (
                        SELECT r.gid AS recording_mbid
                             , array_agg(jsonb_build_array(t.name, count, a.gid, g.gid)) AS artist_tags
                          FROM recording r
                          JOIN artist_credit ac
                            ON r.artist_credit = ac.id
                          JOIN artist_credit_name acn
                            ON acn.artist_credit = ac.id
                          JOIN artist a
                            ON acn.artist = a.id
                          JOIN artist_tag at
                            ON at.artist = a.id
                          JOIN tag t
                            ON at.tag = t.id
                     LEFT JOIN genre g
                            ON t.name = g.name
                         WHERE count > 0
--AND r.gid in ('e97f805a-ab48-4c52-855e-07049142113d')
                         GROUP BY r.gid
               )
                        SELECT recording_links
                             , artist_data
                             , artist_tags
                             , recording_tags
                             , r.length
                             , r.gid::TEXT as recording_mbid
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
                     LEFT JOIN artist_data ard
                            ON ard.gid = r.gid
                     LEFT JOIN recording_rels rrl
                            ON rrl.gid = r.gid
                     LEFT JOIN recording_tags rt
                            ON rt.recording_mbid = r.gid
                     LEFT JOIN artist_tags ats
                            ON ats.recording_mbid = r.gid
--WHERE r.gid in ('e97f805a-ab48-4c52-855e-07049142113d')
                      GROUP BY r.gid, r.length, recording_links, recording_tags, artist_data, artist_tags"""

#WHERE r.gid in ('e97f805a-ab48-4c52-855e-07049142113d')
#AND r.gid in ('e97f805a-ab48-4c52-855e-07049142113d')

    log("mb metadata cache: start")

    # Create the dest table (perhaps dropping the old one first)

    log("mb metadata cache: drop old tables, create new tables")
    create_tables(lb_conn)

    rows = []
    serial = 1
    log("mb metadata cache: execute query (gonna be loooooong!)")
    mb_curs.execute(query)
    total_rows = mb_curs.rowcount
    log(f"mb metadata cache: {total_rows} recordings in result")

    row_count = 0
    while True:
        row = mb_curs.fetchone()
        if not row:
            break

        data = create_json_data(row)
        try:
            rows.append((serial, row["recording_mbid"], "false", *data))
        except Exception as err:
            print(row["recording_mbid"])
            print(str(err))
            return

        serial += 1

        if len(rows) >= BATCH_SIZE:
            insert_rows(lb_curs, "tmp_mb_metadata_cache", rows)
            mb_conn.commit()
            rows = []

            if serial % 100000 == 0:
                log("mb metadata cache: inserted %d rows. %.1f%%" % (serial, 100 * serial / total_rows))

    if rows:
        insert_rows(lb_curs, "tmp_mb_metadata_cache", rows)
        lb_conn.commit()

    log("mb metadata cache: inserted %d rows total." % (serial - 1))
    log("mb metadata cache: create indexes")
    create_indexes(lb_conn)

    log("mb metadata cache: swap tables and indexes into production.")
#    swap_table_and_indexes(lb_conn)

    log("mb metadata cache: done")


def create_mb_metadata_cache():
    psycopg2.extras.register_uuid()
    with psycopg2.connect(config.MBID_MAPPING_DATABASE_URI) as mb_conn:
        with mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs:
            with psycopg2.connect(config.TIMESCALE_DATABASE_URI) as lb_conn:
                with lb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as lb_curs:
                    create_cache(mb_conn, mb_curs, lb_conn, lb_curs)
