import os
import subprocess
from time import sleep
from threading import Thread, get_ident

import psycopg2
from psycopg2.extensions import register_adapter
import requests

from brainzutils import metrics, cache
import config
from mapping.cube import Cube, adapt_cube
from mapping.utils import log

register_adapter(Cube, adapt_cube)

# max number of threads to use -- with 2 we don't need to worry about rate limiting.
MAX_THREADS = 2

# The number of items to compare in one batch
SYNC_BATCH_SIZE = 10000

# cache key for the last_updated timestamp for the sync
LAST_UPDATED_CACHE_KEY = "mbid.release_color_timestamp"


def process_image(filename, mime_type):
    """ Process the downloaded image with netpbm to scale it to 1 pixel
        and return the (reg, green, blue) tuple """

    with open(filename, "rb") as raw:
        proc = subprocess.Popen(["jpegtopnm", filename],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        tmp = proc.communicate(raw.read())

    proc = subprocess.Popen(["pnmscale", "-xsize", "1", "-ysize", "1"],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    out = proc.communicate(tmp[0])

    lines = out[0].split(b"\n", 3)
    if lines[0].startswith(b"P6"):  # PPM
        return lines[3][0], lines[3][1], lines[3][2]

    if lines[0].startswith(b"P5"):  # PGM
        return lines[3][0], lines[3][0], lines[3][0]

    raise RuntimeError


def insert_row(release_mbid, red, green, blue, caa_id, year):
    """ Insert a row into release_color mapping """

    with psycopg2.connect(config.SQLALCHEMY_DATABASE_URI) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
            sql = """INSERT INTO release_color (release_mbid, red, green, blue, color, caa_id, year)
                          VALUES (%s, %s, %s, %s, %s::cube, %s, %s)
                     ON CONFLICT DO NOTHING"""

            args = (release_mbid, red, green, blue,
                    Cube(red, green, blue), caa_id, year)
            try:
                curs.execute(sql, args)
                conn.commit()
            except psycopg2.IntegrityError:
                conn.rollback()


def process_row(row):
    """ Process one CAA query row, by fetching the 250px thumbnail,
        process the color, then import into the DB """

    sleep_duration = 2
    while True:
        headers = {
            'User-Agent': 'ListenBrainz HueSound Color Bot ( rob@metabrainz.org )'
        }
        release_mbid, caa_id = row["release_mbid"], row["caa_id"]
        url = f"https://archive.org/download/mbid-{release_mbid}/mbid-{release_mbid}-{caa_id}_thumb250.jpg"
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            filename = "/tmp/release-colors-%s.img" % get_ident()
            with open(filename, 'wb') as f:
                for chunk in r:
                    f.write(chunk)

            try:
                red, green, blue = process_image(filename, row["mime_type"])
                insert_row(row["release_mbid"], red, green, blue, row["caa_id"], row["year"])
                log("%s %s: (%s, %s, %s)" %
                    (row["caa_id"], row["release_mbid"], red, green, blue))
            except Exception as err:
                log("Could not process %s" % url)
                log(err)

            os.unlink(filename)
            break

        if r.status_code == 403:
            break

        if r.status_code == 404:
            break

        if r.status_code == 429:
            log("Exceeded rate limit. sleeping %d seconds." % sleep_duration)
            sleep(sleep_duration)
            sleep_duration *= 2
            if sleep_duration > 100:
                return

            continue

        if r.status_code == 503:
            log("Service not available. sleeping %d seconds." % sleep_duration)
            sleep(sleep_duration)
            sleep_duration *= 2
            if sleep_duration > 100:
                return
            continue

        log("Unhandled %d" % r.status_code)
        break


def delete_from_lb(lb_conn, caa_id):
    """ Delete a piece of coverart from the release_color table. """

    with lb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as lb_curs:
        lb_curs.execute("""DELETE FROM release_color WHERE caa_id = %s """, (caa_id,))
        lb_conn.commit()


def process_cover_art(threads, row):
    """ Process one row of the CAA query, waiting for a thread to free up.
        This function blocks until a thread is available. """

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
    """ Given the currently active threads, wait for all active threads to finish. """

    while len(threads) > 0:
        for i, thread in enumerate(threads):
            if not thread.is_alive():
                thread.join()
                threads.pop(i)
                break
        else:
            sleep(.001)


def get_cover_art_counts(mb_curs, lb_curs):
    """ Fetch the cover art counts from the CAA and the release_color table. """

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


def get_last_updated_from_caa():
    """ Fetch the last_updated (last date_updated) value from the CAA table """

    with psycopg2.connect(config.MB_DATABASE_STANDBY_URI) as mb_conn, \
            mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs:
        mb_curs.execute("""SELECT max(date_uploaded) AS date_uploaded
                             FROM cover_art_archive.cover_art""")
        last_updated = None
        row = mb_curs.fetchone()
        if row:
            try:
                last_updated = row["date_uploaded"]
            except ValueError:
                pass

        return last_updated


def sync_release_color_table():
    """ Top level function to sync the two CAA and LB cover art tables
        by fetching all rows sorted by caa_id and adding or removing
        cover art as needed. """

    cache.init(host=config.REDIS_HOST, port=config.REDIS_PORT,
               namespace=config.REDIS_NAMESPACE)

    log("cover art sync starting...")
    mb_query = """SELECT caa.id AS caa_id
                       , r.id AS release_id
                       , r.gid AS release_mbid
                       , mime_type
                       , year
                    FROM cover_art_archive.cover_art caa
                    JOIN cover_art_archive.cover_art_type cat
                      ON cat.id = caa.id
                    JOIN musicbrainz.release r
                      ON caa.release = r.id
                    JOIN musicbrainz.release_first_release_date rfrd
                      ON rfrd.release = r.id
                   WHERE type_id = 1
                     AND caa.id > %s
                ORDER BY caa.id
                   LIMIT %s"""

    lb_query = """ SELECT caa_id
                     FROM release_color
                    WHERE caa_id > %s
                 ORDER BY caa_id
                    LIMIT %s"""

    compare_coverart(mb_query, lb_query, 0, 0, "caa_id", "caa_id")

    # set the cache key so that the incremental update starts at the right place
    cache.set(LAST_UPDATED_CACHE_KEY, datetime.datetime.now(), expirein=0, encode=True)


def incremental_update_release_color_table():
    """ Incrementally update the cover art mapping. This is designed to run hourly
        and save a last_updated timestamp in the cache. If the cache value cannot be
        found, a complete sync is run instead and the cache value is set. """

    cache.init(host=config.REDIS_HOST, port=config.REDIS_PORT,
               namespace=config.REDIS_NAMESPACE)

    try:
        last_updated = cache.get(LAST_UPDATED_CACHE_KEY, decode=True) or None
    except Exception:
        last_updated = None

    if not last_updated:
        log("No timestamp found, performing full sync")
        sync_release_color_table()
        last_updated = get_last_updated_from_caa()
        cache.set(LAST_UPDATED_CACHE_KEY, last_updated,
                  expirein=0, encode=True)
        return

    log("cover art incremental update starting...")
    mb_query = """SELECT caa.id AS caa_id
                       , r.id AS release_id
                       , r.gid AS release_mbid
                       , mime_type
                       , date_uploaded
                       , year
                    FROM cover_art_archive.cover_art caa
                    JOIN cover_art_archive.cover_art_type cat
                      ON cat.id = caa.id
                    JOIN musicbrainz.release r
                      ON caa.release = r.id
               LEFT JOIN musicbrainz.release_first_release_date rfrd
                      ON rfrd.release = r.id
                   WHERE type_id = 1
                     AND caa.date_uploaded > %s
                ORDER BY caa.date_uploaded
                   LIMIT %s"""

    compare_coverart(mb_query, None, last_updated, None,
                     "date_uploaded", "last_updated")

    last_updated = get_last_updated_from_caa()
    cache.set(LAST_UPDATED_CACHE_KEY, last_updated, expirein=0, encode=True)


def compare_coverart(mb_query, lb_query, mb_caa_index, lb_caa_index, mb_compare_key, lb_compare_key):
    """ The core cover art comparison function. Given two sets of queries, index values, and 
        comparison keys this function can perform a complete sync as well as an incremental update.

        The queries must fetch chunks of data from the MB and LB tables ordered by
        the corresponding compare key. The starting indexes (the current comparison index
        into the data) must be provided and match the type of the comparison keys. """

    with psycopg2.connect(config.MB_DATABASE_STANDBY_URI) as mb_conn, \
            mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs, \
            psycopg2.connect(config.SQLALCHEMY_DATABASE_URI) as lb_conn, \
            lb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as lb_curs:

        log("MB: ", config.MB_DATABASE_STANDBY_URI)
        log("LB: ", config.SQLALCHEMY_DATABASE_URI)

        mb_count, lb_count = get_cover_art_counts(mb_curs, lb_curs)
        log("CAA count: %d" % (mb_count,))
        log("LB count: %d" % (lb_count,))

        threads = []
        mb_row = None
        lb_row = None

        mb_rows = []
        lb_rows = []

        mb_done = False
        lb_done = True if lb_query is None else False

        extra = 0
        missing = 0
        processed = 0

        while True:
            if len(mb_rows) == 0 and not mb_done:
                mb_curs.execute(mb_query, (mb_caa_index, SYNC_BATCH_SIZE))
                mb_rows = mb_curs.fetchall()
                if len(mb_rows) == 0:
                    mb_done = True

            if len(lb_rows) == 0 and not lb_done:
                lb_curs.execute(lb_query, (lb_caa_index, SYNC_BATCH_SIZE))
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
                log("processed %d of %d: missing %d extra %d" % (processed, mb_count, missing, extra))

            # If the item is in MB, but not in LB, add to LB
            if lb_row is None or mb_row[mb_compare_key] < lb_row[lb_compare_key]:
                process_cover_art(threads, mb_row)
                missing += 1
                mb_caa_index = mb_row[mb_compare_key]
                mb_row = None
                continue

            # If the item is in LB, but not in MB, remove from LB
            if mb_row is None or mb_row[mb_compare_key] > lb_row[lb_compare_key]:
                extra += 1
                delete_from_lb(lb_conn, lb_row[lb_compare_key])
                lb_caa_index = lb_row[lb_compare_key]
                lb_row = None
                continue

            # If the caa_id is present in both, skip both
            if mb_row[mb_compare_key] == lb_row[lb_compare_key]:
                mb_caa_index = mb_row[mb_compare_key]
                lb_caa_index = lb_row[lb_compare_key]
                lb_row = None
                mb_row = None
                continue

            assert False

        join_threads(threads)
        log("Finished! added/skipped %d removed %d from release_color" % (missing, extra))

        mb_count, lb_count = get_cover_art_counts(mb_curs, lb_curs)
        log("CAA count: %d" % (mb_count,))
        log("LB count: %d" % (lb_count,))

        metrics.init("listenbrainz")
        metrics.set(
            "listenbrainz-caa-mapper",
            caa_front_count=mb_count,
            lb_caa_count=lb_count
        )
