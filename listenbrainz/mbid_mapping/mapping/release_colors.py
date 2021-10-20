import os
import re
import subprocess
from time import sleep
from threading import Thread, get_ident

import requests

import psycopg2
from psycopg2.errors import OperationalError
from psycopg2.extensions import register_adapter

from mapping.cube import Cube, adapt_cube
from mapping.utils import log
import config


register_adapter(Cube, adapt_cube)

MAX_THREADS = 16
SYNC_BATCH_SIZE = 10000


def process_image(filename, mime_type):

    with open(filename, "rb") as raw:
        proc = subprocess.Popen(["file", filename], stdout=subprocess.PIPE)
        tmp = proc.communicate(raw.read())
        proc = subprocess.Popen(["jpegtopnm", filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        tmp = proc.communicate(raw.read())

    proc = subprocess.Popen(["pnmscale", "-xsize", "1", "-ysize", "1"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    out = proc.communicate(tmp[0])

    lines = out[0].split(b"\n", 3)
    if lines[0].startswith(b"P6"):  # PPM
        return (lines[3][0], lines[3][1], lines[3][2])

    if lines[0].startswith(b"P5"):  # PGM
        return (lines[3][0], lines[3][0], lines[3][0])

    raise RuntimeError


def insert_row(release_mbid, red, green, blue, caa_id):

    # FIX THIS
    with psycopg2.connect(config.LB_DATABASE_URI) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
            sql = """INSERT INTO release_color (release_mbid, red, green, blue, color, caa_id)
                          VALUES (%s, %s, %s, %s, %s::cube, %s)"""
            args = (release_mbid, red, green, blue, Cube(red, green, blue), caa_id)
            try:
                curs.execute(sql, args)
                conn.commit()
            except psycopg2.IntegrityError:
                conn.rollback()



def process_row(row):
    while True:
        headers = { 'User-Agent': 'ListenBrainz HueSound Color Bot ( rob@metabrainz.org )' }
        url = "https://beta.coverartarchive.org/release/%s/%d-250.jpg" % (row["release_mbid"], row["caa_id"])
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            # TODO: Use proper file name
            filename = "/tmp/release-colors-%s.img" % get_ident()
            with open(filename, 'wb') as f:
                for chunk in r:
                    f.write(chunk)

            try:
                red, green, blue = process_image(filename, row["mime_type"])
                insert_row(row["release_mbid"], red, green, blue, row["caa_id"])
                print("%s %s: (%s, %s, %s)" % (row["caa_id"], row["release_mbid"], red, green, blue))
            except Exception as err:
                print("Could not process %s" % url)
                print(err)

            os.unlink(filename)

            break

        if r.status_code == 403:
            print("Got 403, skipping %s" % url)
            break

        if r.status_code == 404:
            print("Got 404, skipping %s" % url)
            break
            
        if r.status_code in (503, 429):
            print("Exceeded rate limit. sleeping 2 seconds.")
            sleep(2)
            continue

        print("Unhandled %d" % r.status_code)
        break


def delete_from_lb(caa_id):
    with psycopg2.connect(config.LB_DATABASE_URI) as lb_conn:
        with lb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as lb_curs:
            lb_curs.execute("""DELETE FROM release_color WHERE caa_id = %s """, (caa_id,))


def process_cover_art(threads, row):

    while len(threads) == MAX_THREADS:
        for i, thread in enumerate(threads):
            if not thread.is_alive():
                thread.join()
                threads.pop(i)
                break
        else:
            sleep(.001)

    t = Thread(target=process_row, args=(row,))
    t.start()
    threads.append(t)


def join_threads(threads):

    while len(threads) > 0:
        for i, thread in enumerate(threads):
            if not thread.is_alive():
                thread.join()
                threads.pop(i)
                break
        else:
            sleep(.001)

def get_cover_art_counts(mb_curs, lb_curs):

    mb_curs.execute("""SELECT COUNT(*)
                         FROM cover_art_archive.cover_art caa
                         JOIN cover_art_archive.cover_art_type cat
                           ON cat.id = caa.id
                        WHERE type_id = 1""")
    row = mb_curs.fetchone()
    mb_count = row["count"]

    lb_curs.execute("SELECT COUNT(*) FROM release_color")
    row = lb_curs.fetchone()
    lb_count = row["count"]

    return mb_count, lb_count


def sync_release_color_table():

    log("cover art sync starting...")
    caa_query = """SELECT caa.id AS caa_id
                        , release AS release_id
                        , release.gid AS release_mbid
                        , mime_type
                     FROM cover_art_archive.cover_art caa
                     JOIN cover_art_archive.cover_art_type cat
                       ON cat.id = caa.id
                     JOIN musicbrainz.release
                       ON caa.release = release.id
                    WHERE type_id = 1
                      AND caa.id > %s
                 ORDER BY caa.id
                    LIMIT %s"""

    lb_query = """ SELECT caa_id
                     FROM release_color
                    WHERE caa_id > %s
                 ORDER BY caa_id
                    LIMIT %s"""

    mb_caa_id = 0
    lb_caa_id = 0

    with psycopg2.connect(config.MBID_MAPPING_DATABASE_URI) as mb_conn:
        with mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs:
            with psycopg2.connect(config.LB_DATABASE_URI) as lb_conn:
                with lb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as lb_curs:

                    mb_count, lb_count = get_cover_art_counts(mb_curs, lb_curs)
                    print("%d items in MB\n%d items in LB" % (mb_count, lb_count))

                    threads = []
                    mb_row = None
                    lb_row = None

                    mb_rows = []
                    lb_rows = []

                    mb_done = False
                    lb_done = False

                    extra = 0
                    missing = 0
                    processed = 0

                    while True:
                        if len(mb_rows) == 0 and not mb_done:
                            mb_curs.execute(caa_query, (mb_caa_id, SYNC_BATCH_SIZE))
                            mb_rows = mb_curs.fetchall()
                            if len(mb_rows) == 0:
                                mb_done = True

                        if len(lb_rows) == 0 and not lb_done:
                            lb_curs.execute(lb_query, (lb_caa_id, SYNC_BATCH_SIZE))
                            lb_rows = lb_curs.fetchall()
                            if len(lb_rows) == 0:
                                lb_done = True
                            
                        if not mb_row and len(mb_rows) > 0:
                            mb_row = mb_rows.pop(0)

                        if not lb_row and len(lb_rows) > 0:
                            lb_row = lb_rows.pop(0)

                        if not lb_row and not mb_row:
                            break

                        processed += 1
                        if processed % 100000 == 0:
                            print("processed %d of %d: missing %d extra %d" % (processed, mb_count, missing, extra))

                        # If the item is in MB, but not in LB, add to LB
                        if lb_row is None or mb_row["caa_id"] < lb_row["caa_id"]:
                            process_cover_art(threads, mb_row)
                            missing += 1
                            mb_caa_id = mb_row["caa_id"]
                            mb_row = None
                            continue

                        # If the item is in LB, but not in MB, remove from LB
                        if mb_row is None or mb_row["caa_id"] > lb_row["caa_id"]:
                            extra += 1
                            delete_from_lb(lb_row["caa_id"])
                            lb_caa_id = lb_row["caa_id"]
                            lb_row = None
                            continue

                        # If the caa_id is present in both, skip both
                        if mb_row["caa_id"] == lb_row["caa_id"]:
                            mb_caa_id = mb_row["caa_id"]
                            lb_caa_id = lb_row["caa_id"]
                            lb_row = None
                            mb_row = None
                            continue

                        assert False

                    join_threads(threads)

                    mb_count, lb_count = get_cover_art_counts(mb_curs, lb_curs)

                    print("Finished! added/skipped %d removed %d from release_color" % (missing, extra))
                    print("%d items in MB\n%d items in LB" % (mb_count, lb_count))
                    print("difference: %d items" % (mb_count - lb_count))
