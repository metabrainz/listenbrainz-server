import re
import subprocess
from time import sleep

import requests

import psycopg2
from psycopg2.errors import OperationalError

from mapping.utils import log
import config

def process_image(filename, mime_type):

    program = mime_type[6:] + "topnm"

    with open(filename, "rb") as raw:
        proc = subprocess.Popen([program, filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        tmp = proc.communicate(raw.read())

    proc = subprocess.Popen(["pnmscale", "-xsize", "1", "-ysize", "1"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    out = proc.communicate(tmp[0])

    lines = out[0].split(b"\n", 3)
    return (lines[3][0], lines[3][1], lines[3][2])


def download_cover_art():

    log("download cover art starting...")
    query = """SELECT caa.id AS caa_id
                    , release AS release_id
                    , release.gid AS release_mbid
                    , mime_type
                 FROM cover_art_archive.cover_art caa
                 JOIN musicbrainz.release
                   ON caa.release = release.id
                LIMIT 100"""
#             ORDER BY release"""

    with psycopg2.connect(config.MBID_MAPPING_DATABASE_URI) as mb_conn:
        with mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs:

            log("execute query")
            mb_curs.execute(query)
            log("process rows")
            while True:
                row = mb_curs.fetchone()
                if not row:
                    break

                while True:
                    url = "https://coverartarchive.org/release/%s/%d-250.jpg" % (row["release_mbid"], row["caa_id"])
                    r = requests.get(url)
                    if r.status_code == 200: 
                        if row["mime_type"] == "application/pdf":
                            # TODO Skip this in the future
                            continue

                        # TODO: Use proper file name
                        filename = "/tmp/release-colors.img"
                        with open(filename, 'wb') as f:
                            for chunk in r:
                                f.write(chunk)

                        red, green, blue = process_image(filename, row["mime_type"]) 
                        print("%s: (%s, %s, %s)" % (row["release_mbid"], red, green, blue))
                        break

                    if r.status_code == 503:
                        print("Exceeded rate limit. sleeing 2 seconds.")
                        sleep(2)
                        continue

                    print("Unhandled %d" % r.status_code)
                    break
