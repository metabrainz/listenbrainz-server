import sys
import pprint
import operator
import datetime
import subprocess
from time import time
import re

import ujson
import psycopg2
from psycopg2.extras import execute_values
from psycopg2.errors import OperationalError, DuplicateTable, UndefinedObject
from mapping.utils import create_schema, insert_rows

import config
from mapping.formats import create_formats_table


BATCH_SIZE = 5000

# This query will fetch all release groups for single artist release groups and order them
# so that early digital albums are preferred.

SELECT_RELEASES_QUERY = '''
INSERT INTO mapping.recording_pair_releases (release)
      SELECT r.id
      FROM musicbrainz.release_group rg 
      JOIN musicbrainz.release r ON rg.id = r.release_group 
      JOIN musicbrainz.release_country rc ON rc.release = r.id 
      JOIN musicbrainz.medium m ON m.release = r.id 
      JOIN musicbrainz.medium_format mf ON m.format = mf.id 
      JOIN mapping.format_sort fs ON mf.id = fs.format
JOIN musicbrainz.artist_credit ac ON rg.artist_credit = ac.id
JOIN musicbrainz.release_group_primary_type rgpt ON rg.type = rgpt.id   
FULL OUTER JOIN musicbrainz.release_group_secondary_type_join rgstj ON rg.id = rgstj.release_group   
FULL OUTER JOIN musicbrainz.release_group_secondary_type rgst ON rgstj.secondary_type = rgst.id
     WHERE rg.artist_credit != 1 
     %s
   ORDER BY
            rg.type, rgst.id desc, fs.sort, 
            to_date(coalesce(date_year, 9999)::TEXT || '-' || coalesce(date_month, 1)::TEXT || '-' || coalesce(date_day, 1)::TEXT, 'YYYY-MM-DD'), 
            country, rg.artist_credit, rg.name
'''
SELECT_RELEASES_QUERY_WHERE_CLAUSE = 'AND rg.artist_credit = 1160983'

SELECT_RECORDING_PAIRS_QUERY = '''
    SELECT lower(musicbrainz.musicbrainz_unaccent(r.name)) as recording_name, r.id as recording_id, 
           lower(musicbrainz.musicbrainz_unaccent(ac.name)) as artist_credit_name, ac.id as artist_credit_id,
           lower(musicbrainz.musicbrainz_unaccent(rl.name)) as release_name, rl.id as release_id,
           rpr.id
      FROM recording r
      JOIN artist_credit ac ON r.artist_credit = ac.id
      JOIN artist_credit_name acn ON ac.id = acn.artist_credit
      JOIN track t ON t.recording = r.id
      JOIN medium m ON m.id = t.medium
      JOIN release rl ON rl.id = m.release
      JOIN mapping.recording_pair_releases rpr ON rl.id = rpr.release
    GROUP BY rpr.id, ac.id, rl.id, artist_credit_name, r.id, r.name, release_name
    ORDER BY ac.id, rpr.id
'''

CREATE_RECORDING_PAIRS_TABLE_QUERY = '''
    CREATE TABLE mapping.recording_artist_credit_pairs (
        recording_name            TEXT NOT NULL,
        recording_id              INTEGER NOT NULL, 
        artist_credit_name        TEXT NOT NULL,
        artist_credit_id          INTEGER NOT NULL,
        release_name              TEXT NOT NULL,
        release_id                INTEGER NOT NULL
    )
'''

CREATE_RECORDING_PAIR_RELEASES_TABLE_QUERY = '''
    CREATE TABLE mapping.recording_pair_releases (
        id      SERIAL, 
        release INTEGER
    )
'''

CREATE_RECORDING_PAIRS_INDEXES_QUERY = '''
    CREATE INDEX artist_credit_name_ndx_recording_artist_credit_pairs 
        ON mapping.recording_artist_credit_pairs(artist_credit_name);
'''

CREATE_RELEASES_SORT_INDEX = '''
    CREATE INDEX recording_pair_releases_id
        ON mapping.recording_pair_releases(id)
'''

CREATE_RELEASES_ID_INDEX = '''
    CREATE INDEX recording_pair_releases_release
        ON mapping.recording_pair_releases(release)
'''

def create_tables(mb_conn):


    # drop/create finished table from MB
    try:
        with mb_conn.cursor() as curs:
            curs.execute("DROP TABLE mapping.recording_artist_credit_pairs")
        mb_conn.commit()
    except psycopg2.errors.UndefinedTable as err:
        mb_conn.rollback()

    try:
        with mb_conn.cursor() as curs:
            curs.execute(CREATE_RECORDING_PAIRS_TABLE_QUERY)
            curs.execute("ALTER TABLE mapping.recording_artist_credit_pairs OWNER TO musicbrainz")
        mb_conn.commit()

    except OperationalError as err:
        print("failed to create recording pair table")
        mb_conn.rollback()


    # Drop/create temp table from MB DB
    try:
        with mb_conn.cursor() as curs:
            curs.execute("DROP TABLE mapping.recording_pair_releases")
        mb_conn.commit()
    except psycopg2.errors.UndefinedTable as err:
        mb_conn.rollback()

    try:
        with mb_conn.cursor() as curs:
            curs.execute(CREATE_RECORDING_PAIR_RELEASES_TABLE_QUERY)
            curs.execute("ALTER TABLE mapping.recording_pair_releases OWNER TO musicbrainz")
        mb_conn.commit()

    except OperationalError as err:
        print("failed to create recording pair releases table")
        mb_conn.rollback()

    try:
        create_formats_table(mb_conn)
    except (psycopg2.errors.OperationalError, psycopg2.errors.UndefinedTable) as err:
        print("failed to create recording pair releases table")
        mb_conn.rollback()


def create_indexes(conn):
    try:
        with conn.cursor() as curs:
            curs.execute(CREATE_RECORDING_PAIRS_INDEXES_QUERY)
        conn.commit()
    except OperationalError as err:
        print("failed to create recording pair index", err)
        conn.rollback()


def create_temp_release_table(conn, stats):

    with conn.cursor() as curs:
        print("Run select releases query")
        if config.USE_MINIMAL_DATASET:
            print("Using a minimal dataset!")
            curs.execute(SELECT_RELEASES_QUERY % SELECT_RELEASES_QUERY_WHERE_CLAUSE)
        else:
            curs.execute(SELECT_RELEASES_QUERY % "")
        curs.execute(CREATE_RELEASES_ID_INDEX)
        curs.execute(CREATE_RELEASES_SORT_INDEX)
        curs.execute("SELECT COUNT(*) from mapping.recording_pair_releases")
        stats["recording_pair_release_count"] = curs.fetchone()[0]
        curs.execute("SELECT COUNT(*) from musicbrainz.release")
        stats["mb_release_count"] = curs.fetchone()[0]

    return stats


def create_pairs():

    stats = {}
    stats["started"] = datetime.datetime.utcnow().isoformat()
    stats["git commit hash"] = subprocess.getoutput("git rev-parse HEAD")

    with psycopg2.connect(config.DB_CONNECT_MB) as mb_conn:
        with mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs:

            # Create the dest table (perhaps dropping the old one first)
            print("Drop/create pairs table")
            create_schema(mb_conn)
            create_tables(mb_conn)

            print("select releases from MB")
            stats = create_temp_release_table(mb_conn, stats)

            mb_curs.execute("SELECT COUNT(*) from musicbrainz.recording")
            stats["mb_recording_count"] = mb_curs.fetchone()[0]

            with mb_conn.cursor() as mb_curs2:

                rows = []
                last_ac_id = None
                artist_recordings = {}
                count = 0
                print("Run fetch recordings query")
                mb_curs.execute(SELECT_RECORDING_PAIRS_QUERY)
                print("Fetch recordings and insert")
                while True:
                    row = mb_curs.fetchone()
                    if not row:
                        break

                    if not last_ac_id:
                        last_ac_id = row['artist_credit_id']

                    if row['artist_credit_id'] != last_ac_id:
                        # insert the rows that made it
                        rows.extend(artist_recordings.values())
                        artist_recordings = {}

                        if len(rows) > BATCH_SIZE:
                            insert_rows(mb_curs2, "mapping.recording_artist_credit_pairs", rows)
                            count += len(rows)
                            mb_conn.commit()
                            print("inserted %d rows." % count)
                            rows = []

                    recording_name = row['recording_name']
                    artist_credit_name = row['artist_credit_name']
                    release_name = row['release_name']
                    if config.REMOVE_NON_WORD_CHARS:
                        recording_name = re.sub(r'\W+', '', recording_name)
                    if recording_name not in artist_recordings:
                        if config.REMOVE_NON_WORD_CHARS:
                            artist_credit_name = re.sub(r'\W+', '', artist_credit_name)
                            release_name = re.sub(r'\W+', '', release_name)
                        artist_recordings[recording_name] = (recording_name, row['recording_id'], 
                            artist_credit_name, row['artist_credit_id'], release_name, row['release_id'])

                    last_ac_id = row['artist_credit_id']


                rows.extend(artist_recordings.values())
                if rows:
                    insert_rows(mb_curs2, "mapping.recording_artist_credit_pairs", rows)
                    mb_conn.commit()
                    count += len(rows)


            print("inserted %d rows total." % count)
            stats["recording_artist_pair_count"] = count

            print("Create indexes")
            create_indexes(mb_conn)


    stats["completed"] = datetime.datetime.utcnow().isoformat()
    with open("stats/recording-pairs-stats.json", "w") as f:
        f.write(ujson.dumps(stats, indent=2) + "\n")

    print("done")
