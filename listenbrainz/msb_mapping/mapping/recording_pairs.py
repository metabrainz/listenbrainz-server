import sys
import pprint
import operator
import datetime
import subprocess
from time import time, asctime
import re

import ujson
import psycopg2
from psycopg2.extras import execute_values
from psycopg2.errors import OperationalError, DuplicateTable, UndefinedObject
from mapping.utils import create_schema, insert_rows

import config
from mapping.formats import create_formats_table


BATCH_SIZE = 5000

def create_tables(mb_conn):

    # drop/create finished table
    try:
        with mb_conn.cursor() as curs:
            curs.execute("DROP TABLE IF EXISTS mapping.tmp_recording_artist_credit_pairs")
            curs.execute("""CREATE TABLE mapping.tmp_recording_artist_credit_pairs (
                                         recording_name            TEXT NOT NULL,
                                         recording_id              INTEGER NOT NULL, 
                                         artist_credit_name        TEXT NOT NULL,
                                         artist_credit_id          INTEGER NOT NULL,
                                         release_name              TEXT NOT NULL,
                                         release_id                INTEGER NOT NULL)""")
            curs.execute("DROP TABLE IF EXISTS mapping.tmp_recording_pair_releases")
            curs.execute("""CREATE TABLE mapping.tmp_recording_pair_releases (
                                            id      SERIAL, 
                                            release INTEGER)""")
            create_formats_table(mb_conn)
            mb_conn.commit()
    except (psycopg2.errors.OperationalError, psycopg2.errors.UndefinedTable) as err:
        print(asctime(), "failed to create recording pair tables", err)
        mb_conn.rollback()
        raise


def create_indexes(conn):
    try:
        with conn.cursor() as curs:
            curs.execute("""CREATE INDEX tmp_recording_artist_credit_pairs_idx_artist_credit_name
                                      ON mapping.tmp_recording_artist_credit_pairs(artist_credit_name)""")
        conn.commit()
    except OperationalError as err:
        print(asctime(), "failed to create recording pair index", err)
        conn.rollback()
        raise


def create_temp_release_table(conn, stats):

    with conn.cursor() as curs:
        print(asctime(), "Create temp release table: select")
        query = """INSERT INTO mapping.tmp_recording_pair_releases (release)
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
                         ORDER BY rg.type, rgst.id desc, fs.sort, 
                                  to_date(coalesce(date_year, 9999)::TEXT || '-' || 
                                          coalesce(date_month, 1)::TEXT || '-' || 
                                          coalesce(date_day, 1)::TEXT, 'YYYY-MM-DD'), 
                                  country, rg.artist_credit, rg.name"""

        if config.USE_MINIMAL_DATASET:
            print(asctime(), "Create temp release table: Using a minimal dataset!")
            curs.execute(query % 'AND rg.artist_credit = 1160983')
        else:
            curs.execute(query % "")

        print(asctime(), "Create temp release table: create indexes")
        curs.execute("""CREATE INDEX tmp_recording_pair_releases_idx_release
                                  ON mapping.tmp_recording_pair_releases(release)""")
        curs.execute("""CREATE INDEX tmp_recording_pair_releases_idx_id
                                  ON mapping.tmp_recording_pair_releases(id)""")

        curs.execute("SELECT COUNT(*) from mapping.tmp_recording_pair_releases")
        stats["recording_pair_release_count"] = curs.fetchone()[0]
        curs.execute("SELECT COUNT(*) from musicbrainz.release")
        stats["mb_release_count"] = curs.fetchone()[0]

    return stats


def swap_table_and_indexes(conn):

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
            curs.execute("DROP TABLE mapping.recording_pair_releases")
            curs.execute("DROP TABLE mapping.recording_artist_credit_pairs")
            curs.execute("""ALTER TABLE mapping.tmp_recording_artist_credit_pairs
                              RENAME TO recording_artist_credit_pairs""")
            curs.execute("""ALTER TABLE mapping.tmp_recording_pair_releases 
                              RENAME TO recording_pair_releases""")

            curs.execute("""ALTER INDEX mapping.tmp_recording_artist_credit_pairs_idx_artist_credit_name
                              RENAME TO recording_artist_credit_pairs_idx_artist_credit_name""")
            curs.execute("""ALTER INDEX mapping.tmp_recording_pair_releases_idx_release
                              RENAME TO recording_pair_releases_idx_release""")
            curs.execute("""ALTER INDEX mapping.tmp_recording_pair_releases_idx_id
                              RENAME TO recording_pair_releases_idx_id""")
        conn.commit()
    except OperationalError as err:
        print(asctime(), "failed to swap in new recording pair tables", str(err))
        conn.rollback()
        raise

def create_pairs():

    stats = {}
    stats["started"] = datetime.datetime.utcnow().isoformat()
    stats["git commit hash"] = subprocess.getoutput("git rev-parse HEAD")

    with psycopg2.connect(config.DB_CONNECT_MB) as mb_conn:
        with mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs:

            # Create the dest table (perhaps dropping the old one first)
            print(asctime(), "Create pairs: drop old tables, create new tables")
            create_schema(mb_conn)
            create_tables(mb_conn)

            stats = create_temp_release_table(mb_conn, stats)

            mb_curs.execute("SELECT COUNT(*) from musicbrainz.recording")
            stats["mb_recording_count"] = mb_curs.fetchone()[0]

            with mb_conn.cursor() as mb_curs2:

                rows = []
                last_ac_id = None
                artist_recordings = {}
                count = 0
                print(asctime(), "Create pairs: fetch recordings")
                mb_curs.execute("""SELECT lower(musicbrainz.musicbrainz_unaccent(r.name)) as recording_name, r.id as recording_id, 
                                           lower(musicbrainz.musicbrainz_unaccent(ac.name)) as artist_credit_name, ac.id as artist_credit_id,
                                           lower(musicbrainz.musicbrainz_unaccent(rl.name)) as release_name, rl.id as release_id,
                                           rpr.id
                                     FROM recording r
                                     JOIN artist_credit ac ON r.artist_credit = ac.id
                                     JOIN artist_credit_name acn ON ac.id = acn.artist_credit
                                     JOIN track t ON t.recording = r.id
                                     JOIN medium m ON m.id = t.medium
                                     JOIN release rl ON rl.id = m.release
                                     JOIN mapping.tmp_recording_pair_releases rpr ON rl.id = rpr.release
                                    GROUP BY rpr.id, ac.id, rl.id, artist_credit_name, r.id, r.name, release_name
                                    ORDER BY ac.id, rpr.id""")
                print(asctime(), "Create pairs: Insert rows into DB.")
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
                            insert_rows(mb_curs2, "mapping.tmp_recording_artist_credit_pairs", rows)
                            count += len(rows)
                            mb_conn.commit()
                            print(asctime(), "Create pairs: inserted %d rows." % count)
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
                    insert_rows(mb_curs2, "mapping.tmp_recording_artist_credit_pairs", rows)
                    mb_conn.commit()
                    count += len(rows)


            print(asctime(), "Create pairs: inserted %d rows total." % count)
            stats["recording_artist_pair_count"] = count

            print(asctime(), "Create pairs: create indexes")
            create_indexes(mb_conn)

            print(asctime(), "Create pairs: swap tables and indexes into production.")
            swap_table_and_indexes(mb_conn)


    stats["completed"] = datetime.datetime.utcnow().isoformat()
    with open("stats/recording-pairs-stats.json", "w") as f:
        f.write(ujson.dumps(stats, indent=2) + "\n")

    print(asctime(), "done")
