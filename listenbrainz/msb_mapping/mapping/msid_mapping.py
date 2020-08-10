#!/usr/bin/env python3

import sys
import os
import pprint
import psycopg2
import operator
import ujson
from uuid import UUID
import datetime
import subprocess
import re
import gc
from sys import stdout
from time import time
from psycopg2.errors import OperationalError, DuplicateTable, UndefinedObject
from psycopg2.extras import execute_values, register_uuid
from mapping.utils import insert_rows, create_stats_table, log
import config

# The name of the script to be saved in the source field.
SOURCE_NAME = "exact"
NO_PARENS_SOURCE_NAME = "noparens"
MSB_BATCH_SIZE = 20000000


def create_table(conn):
    """
        Given a valid postgres connection, create temporary tables to generate
        the mapping into. These temporary tables will later be swapped out
        with the producton tables in a single transaction.
    """

    try:
        with conn.cursor() as curs:
            curs.execute("DROP TABLE IF EXISTS mapping.tmp_msid_mbid_mapping")
            curs.execute("""CREATE TABLE mapping.tmp_msid_mbid_mapping (
                                         count INTEGER,
                                         msb_artist_name     TEXT,
                                         msb_artist_msid     UUID,
                                         msb_recording_name  TEXT,
                                         msb_recording_msid  UUID,
                                         msb_release_name    TEXT,
                                         msb_release_msid    UUID,
                                         mb_artist_name      TEXT,
                                         mb_artist_credit_id INTEGER,
                                         mb_recording_name   TEXT,
                                         mb_recording_id     INTEGER,
                                         mb_release_name     TEXT,
                                         mb_release_id       INTEGER,
                                         source              TEXT)""")
            create_stats_table(curs)
            conn.commit()
    except DuplicateTable as err:
        log("Cannot drop/create tables: ", str(err))
        conn.rollback()
        raise


def create_indexes(conn):
    """
        Create the indexes on the mapping.
    """

    try:
        with conn.cursor() as curs:
            curs.execute("""CREATE INDEX tmp_msid_mbid_mapping_idx_msb_recording_name
                                      ON mapping.tmp_msid_mbid_mapping(msb_recording_name)""")
            curs.execute("""CREATE INDEX tmp_msid_mbid_mapping_idx_msb_recording_msid
                                      ON mapping.tmp_msid_mbid_mapping(msb_recording_msid)""")
            curs.execute("""CREATE INDEX tmp_msid_mbid_mapping_idx_msb_artist_name
                                      ON mapping.tmp_msid_mbid_mapping(msb_artist_name)""")
            curs.execute("""CREATE INDEX tmp_msid_mbid_mapping_idx_msb_artist_msid
                                      ON mapping.tmp_msid_mbid_mapping(msb_artist_msid)""")
            curs.execute("""CREATE INDEX tmp_msid_mbid_mapping_idx_msb_release_name
                                      ON mapping.tmp_msid_mbid_mapping(msb_release_name)""")
            curs.execute("""CREATE INDEX tmp_msid_mbid_mapping_idx_msb_release_msid
                                      ON mapping.tmp_msid_mbid_mapping(msb_release_msid)""")
            conn.commit()
    except OperationalError as err:
        conn.rollback()
        log("creating indexes failed.")
        raise


def swap_table_and_indexes(conn):
    """
        This function swaps the temporary files that the mapping was written for the
        production tables, inside a single transaction. This should isolate the
        end users from ever seeing any down time in mapping availability.
    """

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
            curs.execute("DROP TABLE mapping.msid_mbid_mapping")
            curs.execute("""ALTER TABLE mapping.tmp_msid_mbid_mapping
                              RENAME TO msid_mbid_mapping""")
            curs.execute("""ALTER INDEX mapping.tmp_msid_mbid_mapping_idx_msb_recording_name
                              RENAME TO msid_mbid_mapping_idx_msb_recording_name""")
            curs.execute("""ALTER INDEX mapping.tmp_msid_mbid_mapping_idx_msb_recording_msid
                              RENAME TO msid_mbid_mapping_idx_msb_recording_msid""")
            curs.execute("""ALTER INDEX mapping.tmp_msid_mbid_mapping_idx_msb_artist_name
                              RENAME TO msid_mbid_mapping_idx_msb_artist_name""")
            curs.execute("""ALTER INDEX mapping.tmp_msid_mbid_mapping_idx_msb_artist_msid
                              RENAME TO msid_mbid_mapping_idx_msb_artist_msid""")
            curs.execute("""ALTER INDEX mapping.tmp_msid_mbid_mapping_idx_msb_release_name
                              RENAME TO msid_mbid_mapping_idx_msb_release_name""")
            curs.execute("""ALTER INDEX mapping.tmp_msid_mbid_mapping_idx_msb_release_msid
                              RENAME TO msid_mbid_mapping_idx_msb_release_msid""")
        conn.commit()
    except OperationalError as err:
        log("failed to swap in new mapping table", str(err))
        conn.rollback()
        raise


def load_MSB_recordings(offset):
    """
        Load a chunk of MSB recordings into ram and sort them, starting at the given offset.
    """

    msb_recordings = []

    count = 0
    with psycopg2.connect(config.DB_CONNECT_MSB) as conn:
        with conn.cursor() as curs:
            query = """SELECT lower(public.unaccent(rj.data->>'artist'::TEXT)::TEXT) AS artist_name, artist as artist_msid,
                              lower(public.unaccent(rj.data->>'title'::TEXT)::TEXT) AS recording_name, r.gid AS recording_msid,
                              lower(public.unaccent(rl.title::TEXT)::TEXT) AS release_name, rl.gid AS release_msid
                         FROM recording r
                         JOIN recording_json rj ON r.data = rj.id
              LEFT OUTER JOIN release rl ON r.release = rl.gid"""

            if config.USE_MINIMAL_DATASET:
                query += """ JOIN artist_credit ac ON ac.gid = artist
                           WHERE ac.gid = '07a5af27-b0ff-41c8-84b1-a41f17b21418'"""

            query += " LIMIT %d OFFSET %d" % (MSB_BATCH_SIZE, offset)
            curs.execute(query)
            while True:
                msb_row = curs.fetchone()
                if not msb_row:
                    break

                artist = msb_row[0]
                artist_msid = msb_row[1]
                recording = msb_row[2]
                recording_msid = msb_row[3]
                release = msb_row[4] or ""
                release_msid = msb_row[5] or None

                if config.REMOVE_NON_WORD_CHARS:
                    artist = re.sub(r'\W+', '', artist)
                    recording = re.sub(r'\W+', '', recording)
                    release = re.sub(r'\W+', '', release)

                msb_recordings.append({
                    "artist_name": artist,
                    "artist_msid": artist_msid,
                    "recording_name": recording,
                    "recording_msid": recording_msid,
                    "release_name": release,
                    "release_msid": release_msid
                })
                count += 1

    if count == 0:
        return None

    return msb_recordings


def load_MB_recordings():
    """
        Load all of the recording artists pairs into ram and sort them for matching.
    """

    mb_recordings = []
    with psycopg2.connect(config.DB_CONNECT_MB) as conn:
        with conn.cursor() as curs:
            query = """SELECT DISTINCT lower(public.unaccent(artist_credit_name::TEXT)) as artist_credit_name, artist_credit_id,
                                       lower(public.unaccent(recording_name::TEXT)) AS recording_name, recording_id,
                                       lower(public.unaccent(release_name::TEXT)) AS release_name, release_id
                         FROM mapping.recording_artist_credit_pairs"""
            if config.USE_MINIMAL_DATASET:
                query += " WHERE artist_credit_id = 1160983"
            curs.execute(query)
            while True:
                mb_row = curs.fetchone()
                if not mb_row:
                    break

                artist = mb_row[0]
                artist_credit_id = int(mb_row[1])
                recording = mb_row[2]
                recording_id = int(mb_row[3])
                release = mb_row[4]
                release_id = int(mb_row[5])
                if config.REMOVE_NON_WORD_CHARS:
                    artist = re.sub(r'\W+', '', artist)
                    recording = re.sub(r'\W+', '', recording)
                    release = re.sub(r'\W+', '', release)

                mb_recordings.append({
                    "artist_name": artist,
                    "artist_credit_id": artist_credit_id,
                    "recording_name": recording,
                    "recording_id": recording_id,
                    "release_name": release,
                    "release_id": release_id,
                })

    log("loaded %d MB recordings, now sorting" % len(mb_recordings))
    mb_recording_index = list(range(len(mb_recordings)))
    mb_recording_index = sorted(mb_recording_index, key=lambda rec: (mb_recordings[rec]["artist_name"], 
                                                                     mb_recordings[rec]["recording_name"]))

    return (mb_recordings, mb_recording_index)


def match_recordings(msb_recordings, msb_recording_index, mb_recordings, mb_recording_index, unmatched=None):
    """
        This function will take the MB recordings, the MSB recordings and their indexes and walk both
        lists in parallel in order to find exact matches between the two. The matches found
        will be return by this function.
    """

    recording_mapping = {}
    mb_index = -1
    msb_index = -1
    msb_row = None
    mb_row = None
    while True:
        if not msb_row:
            try:
                msb_index += 1
                msb_row = msb_recordings[msb_recording_index[msb_index]]
            except IndexError:
                break

        if not mb_row:
            try:
                mb_index += 1
                mb_row = mb_recordings[mb_recording_index[mb_index]]
            except IndexError:
                break

        pp = "%-37s %-37s = %-27s %-37s %s" % (msb_row["artist_name"][0:25], msb_row["recording_name"][0:25],
            mb_row["artist_name"][0:25], mb_row["recording_name"][0:25], msb_row["recording_msid"][0:8])
        if msb_row["artist_name"] > mb_row["artist_name"]:
            if config.SHOW_MATCHES: 
                log("> %s" % pp)
            mb_row = None
            continue

        if msb_row["artist_name"] < mb_row["artist_name"]:
            if config.SHOW_MATCHES: 
                log("< %s" % pp)
            msb_row = None
            continue

        if msb_row["recording_name"] > mb_row["recording_name"]:
            if config.SHOW_MATCHES: 
                log("} %s" % pp)
            if unmatched: unmatched.write("%s\n" % msb_row['recording_msid'])
            mb_row = None
            continue

        if msb_row["recording_name"] < mb_row["recording_name"]:
            if config.SHOW_MATCHES: 
                log("{ %s" % pp)
            if unmatched: unmatched.write("%s\n" % msb_row['recording_msid'])
            msb_row = None
            continue

        if config.SHOW_MATCHES: log("= %s %s %s" % (pp, mb_row["recording_id"], mb_row['release_id']))

        k = "%s=%s" % (msb_row["recording_msid"], mb_row["recording_id"])
        try:
            recording_mapping[k][0] += 1
        except KeyError:
            recording_mapping[k] = [1, msb_recording_index[msb_index], mb_recording_index[mb_index]]

        msb_row = None

    return recording_mapping


def insert_matches(recording_mapping, mb_recordings, msb_recordings, source):
    """
        Take the matched recording mapping and insert them into postgres
    """

    completed = {}
    with psycopg2.connect(config.DB_CONNECT_MB) as conn:
        with conn.cursor() as curs:
            register_uuid(curs)
            rows = []
            total = 0
            for k in recording_mapping.keys():
                a = recording_mapping[k]
                completed[a[0]] = 1
                rows.append((a[0],
                            msb_recordings[a[1]]["artist_name"],
                            msb_recordings[a[1]]["artist_msid"],
                            msb_recordings[a[1]]["recording_name"],
                            msb_recordings[a[1]]["recording_msid"],
                            msb_recordings[a[1]]["release_name"],
                            msb_recordings[a[1]]["release_msid"],
                            mb_recordings[a[2]]["artist_name"],
                            mb_recordings[a[2]]["artist_credit_id"],
                            mb_recordings[a[2]]["recording_name"],
                            mb_recordings[a[2]]["recording_id"],
                            mb_recordings[a[2]]["release_name"],
                            mb_recordings[a[2]]["release_id"],
                            source))
                total += 1

                if len(rows) == 2000:
                    insert_rows(curs, "mapping.tmp_msid_mbid_mapping", rows)
                    rows = []

            insert_rows(curs, "mapping.tmp_msid_mbid_mapping", rows)
            conn.commit()

    msb_recording_index = []
    for i, msb_recording in enumerate(msb_recordings):
        if i in completed:
            continue

        msb_recording_index.append(i)

    msb_recording_index = sorted(msb_recording_index,
                                 key=lambda rec: (msb_recordings[rec]["artist_name"],
                                                  msb_recordings[rec]["recording_name"]))

    return (total, msb_recording_index)


def remove_parens(msb_recordings):
    """
        Take the MSB recordings and if they contain text in () at the end, remove the
        parens in order for running the matching again. This picks up a few more matches.
    """

    for recording in msb_recordings:
        recording["recording_name"] = recording["recording_name"][:recording["recording_name"].find("("):].strip()

    return msb_recordings


def create_mapping():
    """
        This is the heart of the mapper. It sets up the database, loads MB and MSB recordings,
        carries out the matching and writes matches to disk. At the end of this process
        the mapping is swapped from temp tables to the production tables in one transaction.

        During the mapping process stats are kept about how many recordings were matched.
        These are written to the mapping.stats table so they can be displayed as part of
        the labs-api.
    """

    stats = {}
    stats["started"] = datetime.datetime.utcnow().isoformat()
    stats['msb_recording_count'] = 0
    stats['mb_recording_count'] = 0
    stats['msid_mbid_mapping_count'] = 0
    stats['exact_match_count'] = 0
    stats['noparen_match_count'] = 0

    log("Drop old temp table, create new one")
    with psycopg2.connect(config.DB_CONNECT_MB) as conn:
        create_table(conn)

    log("Load MB recordings")
    mb_recordings, mb_recording_index = load_MB_recordings()
    stats['mb_recording_count'] = len(mb_recordings)

    msb_offset = 0
    with open("unmatched_recording_msids.txt", "w") as unmatched:
        while True:
            log("Load MSB recordings at offset %d" % (msb_offset))
            msb_recordings = load_MSB_recordings(msb_offset)
            if not msb_recordings:
                log("  loaded none, we're done!")
                break

            stats['msb_recording_count'] += len(msb_recordings)

            log("  loaded %d items, sorting" % (len(msb_recordings)))
            msb_recording_index = list(range(len(msb_recordings)))
            msb_recording_index = sorted(msb_recording_index, key=lambda rec: (msb_recordings[rec]["artist_name"],
                                                                               msb_recordings[rec]["recording_name"]))

            log("  run exact match")
            recording_mapping = match_recordings(msb_recordings, msb_recording_index, mb_recordings,
                                                 mb_recording_index, unmatched)
            inserted, msb_recording_index = insert_matches(recording_mapping, mb_recordings,
                                                           msb_recordings, SOURCE_NAME)
            stats['msid_mbid_mapping_count'] += inserted
            stats['exact_match_count'] += inserted
            log("  inserted %d exact matches. total: %d" % (inserted, stats['msid_mbid_mapping_count']))

            log("  run no parens match")
            msb_recordings = remove_parens(msb_recordings)
            recording_mapping = match_recordings(msb_recordings, msb_recording_index,
                                                 mb_recordings, mb_recording_index)
            inserted, msb_recording_index = insert_matches(recording_mapping, mb_recordings, msb_recordings,
                                                           NO_PARENS_SOURCE_NAME)
            stats['msid_mbid_mapping_count'] += inserted
            stats['noparen_match_count'] += inserted
            log("  inserted %d no paren matches. total: %d" % (inserted, stats['msid_mbid_mapping_count']))

            stats["msb_coverage"] = int(stats["msid_mbid_mapping_count"] / stats["msb_recording_count"] * 100)
            log("mapping coverage: %d%%" % stats["msb_coverage"])

            msb_recordings = None
            msb_recording_index = None
            gc.collect()

            msb_offset += MSB_BATCH_SIZE

    stats["completed"] = datetime.datetime.utcnow().isoformat()

    with psycopg2.connect(config.DB_CONNECT_MB) as conn:
        log("create indexes")
        create_indexes(conn)
        log("swap tables/indexes")
        swap_table_and_indexes(conn)

    with psycopg2.connect(config.DB_CONNECT_MB) as conn:
        with conn.cursor() as curs:
            curs.execute("""INSERT INTO mapping.mapping_stats (stats) VALUES (%s)""", ((ujson.dumps(stats),)))
        conn.commit()

    log("done")
    print()
