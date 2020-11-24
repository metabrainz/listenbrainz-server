import datetime
import operator
import sys
import re
from time import time, asctime
import typesense
import typesense.exceptions
from unidecode import unidecode

import psycopg2
from psycopg2.extras import execute_values
from psycopg2.errors import OperationalError, DuplicateTable, UndefinedObject
import ujson

from mapping.utils import log
import config

BATCH_SIZE = 5000
COLLECTION_NAME = 'mbid_mapping'

def prepare_string(text):
    return unidecode(re.sub(" +", " ", re.sub(r'[^\w ]+', '', text)).lower())


def build_index():

    client = typesense.Client({
        'nodes': [{
          'host': 'typesense',
          'port': '8108',
          'protocol': 'http',
        }],
        'api_key': config.TYPESENSE_API_KEY,
        'connection_timeout_seconds': 1000000
    })

    schema = {
        'name': COLLECTION_NAME,
        'fields': [
          {
            'name'  :  'combined',
            'type'  :  'string'
          },
          {
            'name'  :  'score',
            'type'  :  'int32'
          },
        ],
        'default_sorting_field': 'score'
    }

    try:
        client.collections[COLLECTION_NAME].delete()
    except typesense.exceptions.ObjectNotFound:
        pass

    client.collections.create(schema)

    with psycopg2.connect(config.DB_CONNECT_MB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:


            curs.execute("SELECT max(score) FROM mapping.mbid_mapping")
            max_score = curs.fetchone()[0]

            query = ("""SELECT recording_name AS recording_name,
                               r.gid AS recording_mbid,
                               release_name AS release_name,
                               rl.gid AS release_mbid,
                               artist_credit_name AS artist_credit_name,
                               artist_credit_id,
                               score
                          FROM mapping.mbid_mapping
                          JOIN recording r
                            ON r.id = recording_id
                          JOIN release rl
                            ON rl.id = release_id""")


            if config.USE_MINIMAL_DATASET:
                query += " WHERE artist_credit_id = 1160983"

            curs.execute(query)
            documents = []
            for i, row in enumerate(curs):
                document = dict(row)
                document['score'] = max_score - document['score'] 
                document['combined'] = prepare_string(document['recording_name'] + " " + document['artist_credit_name'])
                documents.append(document)

                if len(documents) == BATCH_SIZE:
                    client.collections[COLLECTION_NAME].documents.import_(documents)
                    documents = []

                if i and i % 100000 == 0:
                    print(i)

            if documents:
                client.collections[COLLECTION_NAME].documents.import_(documents)
