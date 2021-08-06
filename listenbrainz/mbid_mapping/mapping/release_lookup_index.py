import sys
import re
import time
import datetime

from unidecode import unidecode
import psycopg2
import pysolr

import config
from mapping.utils import log


BATCH_SIZE = 100000
SOLR_HOST = "listenbrainz-solr"
SOLR_PORT = 8983
SOLR_CORE = "release-index"


def build_release_lookup_index():

    solr = pysolr.Solr('http://%s:%d/solr/%s' % (SOLR_HOST, SOLR_PORT, SOLR_CORE), always_commit=True)

    with psycopg2.connect(config.MBID_MAPPING_DATABASE_URI) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:

            query = ("""SELECT ac.id AS artist_credit_id,
                               ac.name AS artist_credit_name,
                               rel.gid AS release_mbid,
                               rel.name AS release_name,
                               array_agg(ARRAY[rec.name, acn2.name]) AS recording_data
                          FROM artist_credit ac
                          JOIN release rel
                            ON rel.artist_credit = ac.id
                          JOIN medium m
                            ON m.release = rel.id
                          JOIN track t
                            ON t.medium = m.id
                          JOIN recording rec
                            ON t.recording = rec.id
                          JOIN artist_credit_name acn2
                            ON rec.artist_credit = acn2.artist_credit
                      GROUP BY ac.id, ac.name, rel.gid, rel.name""")

            log("Run query")
            curs.execute(query)

            docs = []
            batch_count = 0
            for row in curs:
                recording_names = " ".join([name[0] for name in row["recording_data"]])
                recording_artists = " ".join([name[1] for name in row["recording_data"]])
                docs.append({
                    "id": row["release_mbid"],
                    "title": row["release_name"],
                    "artist_credit_id": row["artist_credit_id"],
                    "artist_credit_name": row["artist_credit_name"],
                    "recording_names": recording_names,
                    "recording_artist_credit_names": recording_artists})

                if len(docs) == BATCH_SIZE:
                    solr.add(docs)
                    docs = []
                    batch_count += 1

                    if batch_count % 10 == 0:
                        log("Added %d rows" % (BATCH_SIZE * batch_count))

            if len(docs):
                solr.add(docs)

            log("Done!")


