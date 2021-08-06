import sys
import re
import time
import datetime

from unidecode import unidecode
import psycopg2
import pysolr

import config
from mapping.utils import log


BATCH_SIZE = 5000
SOLR_HOST = "listenbrainz-solr"
SOLR_PORT = 8983


def build_release_lookup_index():

    solr = pysolr.Solr('http://%s:%d/solr/' % (SOLR_HOST, SOLR_PORT), always_commit=False)

    with psycopg2.connect(config.MBID_MAPPING_DATABASE_URI) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:

            query = ("""SELECT ac.id AS artist_credit_id,
                               ac.name AS artist_credit_name,
                               rel.gid AS release_mbid,
                               rel.name AS release_name,
                               array_agg(rec.name) AS recording_names
                          FROM artist_credit ac
                          JOIN release rel
                            ON rel.artist_credit = ac.id
                          JOIN medium m
                            ON m.release = rel.id
                          JOIN track t
                            ON t.medium = m.id
                          JOIN recording rec
                            ON t.recording = rec.id
                      GROUP BY ac.id, ac.name, rel.gid, rel.name""")

            curs.execute(query)

            docs = []
            for row in curs:
                data = {
                    "id": row["release_mbid"],
                    "title": row["release_name"],
                    "artist_credit_id": row["artist_credit_id"]
                }

                for i, artist_credit_name, recording_name in enumerate(zip(row["artist_credit_name"], row["recording_names"])):
                    data["ac_name_%d"] = artist_credit_name
                    data["recording_name_%d"] = recording_name

                docs.append(data)

                if len(docs) == BATCH_SIZE:
                    solr.add(docs)
                    docs = []

            if len(docs):
                solr.add(docs)
