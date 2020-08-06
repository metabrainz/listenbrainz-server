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
from mapping.utils import insert_rows
import config

# The name of the script to be saved in the source field.
SOURCE_NAME = "exact"
NO_PARENS_SOURCE_NAME = "noparens"

MSB_BATCH_SIZE = 20000000

SELECT_MSB_RECORDINGS_QUERY = '''
         SELECT lower(public.unaccent(rj.data->>'artist'::TEXT)::TEXT) AS artist_name, artist as artist_msid,
                lower(public.unaccent(rj.data->>'title'::TEXT)::TEXT) AS recording_name, r.gid AS recording_msid,
                lower(public.unaccent(rl.title::TEXT)::TEXT) AS release_name, rl.gid AS release_msid
           FROM recording r
           JOIN recording_json rj ON r.data = rj.id
LEFT OUTER JOIN release rl ON r.release = rl.gid
                %s
'''
SELECT_MSB_RECORDINGS_QUERY_WHERE_CLAUSE = '''
           JOIN artist_credit ac ON ac.gid = artist
     WHERE ac.gid = '07a5af27-b0ff-41c8-84b1-a41f17b21418'
'''

SELECT_MB_RECORDINGS_QUERY = '''
    SELECT DISTINCT lower(public.unaccent(artist_credit_name::TEXT)) as artist_credit_name, artist_credit_id,
                    lower(public.unaccent(recording_name::TEXT)) AS recording_name, recording_id,
                    lower(public.unaccent(release_name::TEXT)) AS release_name, release_id
      FROM mapping.recording_artist_credit_pairs 
      %s
'''
SELECT_MB_RECORDINGS_QUERY_WHERE_CLAUSE = '''
      WHERE artist_credit_id = 1160983
'''

CREATE_MAPPING_TABLE_QUERY = """
    CREATE TABLE mapping.msid_mbid_mapping (
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
        source              TEXT
    )
"""

CREATE_MAPPING_INDEXES_QUERIES = [
    "CREATE INDEX msid_mbid_mapping_msb_recording_name_ndx ON mapping.msid_mbid_mapping(msb_recording_name)",
    "CREATE INDEX msid_mbid_mapping_msb_recording_msid_ndx ON mapping.msid_mbid_mapping(msb_recording_msid)",
    "CREATE INDEX msid_mbid_mapping_msb_artist_name_ndx ON mapping.msid_mbid_mapping(msb_artist_name)",
    "CREATE INDEX msid_mbid_mapping_msb_artist_msid_ndx ON mapping.msid_mbid_mapping(msb_artist_msid)",
    "CREATE INDEX msid_mbid_mapping_msb_release_name_ndx ON mapping.msid_mbid_mapping(msb_release_name)",
    "CREATE INDEX msid_mbid_mapping_msb_release_msid_ndx ON mapping.msid_mbid_mapping(msb_release_msid)",
]

def create_table(conn):

    with conn.cursor() as curs:
        while True:
            try:
                curs.execute(CREATE_MAPPING_TABLE_QUERY)
                conn.commit() 
                break

            except DuplicateTable as err:
                conn.rollback() 
                curs.execute("DROP TABLE mapping.msid_mbid_mapping")
                conn.commit() 


def create_indexes(conn):

    try:
        with conn.cursor() as curs:
            for query in CREATE_MAPPING_INDEXES_QUERIES:
                print("  ", query)
                curs.execute(query)
            conn.commit()
    except OperationalError as err:
        conn.rollback()
        print("creating indexes failed.")

            
def load_MSB_recordings(stats, offset):

    msb_recordings = []

    count = 0
    with psycopg2.connect(config.DB_CONNECT_MSB) as conn:
        with conn.cursor() as curs:
            if config.USE_MINIMAL_DATASET:
                query = SELECT_MSB_RECORDINGS_QUERY % SELECT_MSB_RECORDINGS_QUERY_WHERE_CLAUSE
            else:
                query = SELECT_MSB_RECORDINGS_QUERY % ""
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
                    "artist_name" : artist,
                    "artist_msid" : artist_msid,
                    "recording_name" : recording,
                    "recording_msid" : recording_msid,
                    "release_name" : release,
                    "release_msid" : release_msid
                })
                count += 1
                if count % 1000000 == 0:
                    print("load MSB %d" % count)

    if count == 0:
        return (stats, None)

    stats["msb_recording_count"] = len(msb_recordings)
    return stats, msb_recordings


def load_MB_recordings(stats):

    mb_recordings = []
    count = 0
    with psycopg2.connect(config.DB_CONNECT_MB) as conn:
        with conn.cursor() as curs:
            if config.USE_MINIMAL_DATASET:
                curs.execute(SELECT_MB_RECORDINGS_QUERY % SELECT_MB_RECORDINGS_QUERY_WHERE_CLAUSE)
            else:
                curs.execute(SELECT_MB_RECORDINGS_QUERY % "")
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
                    "artist_name" : artist,
                    "artist_credit_id" : artist_credit_id,
                    "recording_name" : recording,
                    "recording_id" : recording_id,
                    "release_name" : release,
                    "release_id" : release_id,
                })
                count += 1
                if count % 1000000 == 0:
                    print("load MB %d" % count)

    print("sort MB recordings %d items" % len(mb_recordings))
    mb_recording_index = list(range(len(mb_recordings)))
    mb_recording_index = sorted(mb_recording_index, key=lambda rec: (mb_recordings[rec]["artist_name"], mb_recordings[rec]["recording_name"]))

    return (mb_recordings, mb_recording_index)


def match_recordings(msb_recordings, msb_recording_index, mb_recordings, mb_recording_index, unmatched = None):

    recording_mapping = {}
    mb_index = -1
    msb_index = -1
    msb_row = None
    mb_row = None
    count  = 0
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
            if config.SHOW_MATCHES: print("> %s" % pp)
            mb_row = None
            continue

        if msb_row["artist_name"] < mb_row["artist_name"]:
            if config.SHOW_MATCHES: print("< %s" % pp)
            msb_row = None
            continue

        if msb_row["recording_name"] > mb_row["recording_name"]:
            if config.SHOW_MATCHES: print("} %s" % pp)
            if unmatched: unmatched.write("%s\n" % msb_row['recording_msid'])
            mb_row = None
            continue

        if msb_row["recording_name"] < mb_row["recording_name"]:
            if config.SHOW_MATCHES: print("{ %s" % pp)
            if unmatched: unmatched.write("%s\n" % msb_row['recording_msid'])
            msb_row = None
            continue

        if config.SHOW_MATCHES: print("= %s %s %s" % (pp, mb_row["recording_id"], mb_row['release_id']))

        k = "%s=%s" % (msb_row["recording_msid"], mb_row["recording_id"])
        try:
            recording_mapping[k][0] += 1
        except KeyError:
            recording_mapping[k] = [ 1, msb_recording_index[msb_index], mb_recording_index[mb_index] ]

        count += 1
        msb_row = None
        if count % 1000000 == 0:
            print("%d matches" % count)

    print("  mapping found %d matches out of %d (%d%%)" % (
                len(recording_mapping), 
                len(msb_recordings), 
                len(recording_mapping) * 100 / len(msb_recordings)))

    return recording_mapping


def insert_matches(recording_mapping, mb_recordings, msb_recordings, source):

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
                    source
                    ))
                total += 1

                if len(rows) == 2000:
                    insert_rows(curs, "mapping.msid_mbid_mapping", rows)
                    rows = []

                if total % 1000000 == 0:
                    print("  wrote %d of %d" % (total, len(recording_mapping)))

            insert_rows(curs, "mapping.msid_mbid_mapping", rows)
            conn.commit()

    msb_recording_index = []
    for i, msb_recording in enumerate(msb_recordings):
        if i in completed:
            continue

        msb_recording_index.append(i)

    msb_recording_index = sorted(msb_recording_index, key=lambda rec: (msb_recordings[rec]["artist_name"], msb_recordings[rec]["recording_name"]))

    return (total, msb_recording_index)


def remove_parens(msb_recordings):
    for recording in msb_recordings:
        recording["recording_name"] = recording["recording_name"][:recording["recording_name"].find("("):].strip()

    return msb_recordings


def create_mapping():

    stats = {}
    stats["started"] = datetime.datetime.utcnow().isoformat()
    stats["git commit hash"] = subprocess.getoutput("git rev-parse HEAD")
    stats['msid_mbid_mapping_count'] = 0
    stats['exact_match_count'] = 0
    stats['noparen_match_count'] = 0

    with psycopg2.connect(config.DB_CONNECT_MB) as conn:
        create_table(conn)

    print("Load MB recordings")
    mb_recordings, mb_recording_index = load_MB_recordings(stats)

    msb_offset = 0
    with open("unmatched_recording_msids.txt", "w") as unmatched:
        while True:
            print("Load MSB recordings offset %d" % msb_offset)
            stats, msb_recordings = load_MSB_recordings(stats, msb_offset)
            if not msb_recordings:
                break

            print("  sort MSB recordings %d items" % (len(msb_recordings)))
            msb_recording_index = list(range(len(msb_recordings)))
            msb_recording_index = sorted(msb_recording_index, key=lambda rec: (msb_recordings[rec]["artist_name"], msb_recordings[rec]["recording_name"]))

            print("  match recordings")
            recording_mapping = match_recordings(msb_recordings, msb_recording_index, mb_recordings, mb_recording_index, unmatched)

            print("  insert matches")
            inserted, msb_recording_index = insert_matches(recording_mapping, mb_recordings, msb_recordings, SOURCE_NAME)
            stats['msid_mbid_mapping_count'] += inserted
            stats['exact_match_count'] += inserted

            print("  %s MSB recordings left" % len(msb_recordings))

            print("  remove parens")
            msb_recordings = remove_parens(msb_recordings)

            print("  match recordings")
            recording_mapping = match_recordings(msb_recordings, msb_recording_index, mb_recordings, mb_recording_index)

            print("  insert matches")
            inserted, msb_recording_index = insert_matches(recording_mapping, mb_recordings, msb_recordings, NO_PARENS_SOURCE_NAME)
            stats['msid_mbid_mapping_count'] += inserted
            stats['noparen_match_count'] += inserted

            print("  %s MSB recordings left" % len(msb_recordings))

            msb_recordings = None
            msb_recording_index = None
            gc.collect()

            msb_offset += MSB_BATCH_SIZE

    stats["msb_coverage"] = int(stats["msid_mbid_mapping_count"] / stats["msb_recording_count"] * 100) 
    stats["completed"] = datetime.datetime.utcnow().isoformat()

    print("create indexes")
    with psycopg2.connect(config.DB_CONNECT_MB) as conn:
        create_indexes(conn)

    with open("stats/mapping-stats.json", "w") as f:
        f.write(ujson.dumps(stats, indent=2) + "\n")
