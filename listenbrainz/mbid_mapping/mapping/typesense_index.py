import sys
import re
import time

import typesense
import typesense.exceptions
from unidecode import unidecode
import psycopg2

import config


BATCH_SIZE = 5000
COLLECTION_NAME_PREFIX = 'mbid_mapping_'


def prepare_string(text):
    return unidecode(re.sub(" +", " ", re.sub(r'[^\w ]+', '', text)).lower())


def build_index():

    client = typesense.Client({
        'nodes': [{
          'host': config.TYPESENSE_HOST,
          'port': config.TYPESENSE_PORT,
          'protocol': 'http',
        }],
        'api_key': config.TYPESENSE_API_KEY,
        'connection_timeout_seconds': 1000000
    })

    collection_name = COLLECTION_NAME_PREFIX + str(int(time.time()))
    try:
        print("build index '%s'" % collection_name)
        build(client, collection_name)
    except typesense.exceptions.TypesenseClientError as err:
        print("Cannot build index: ", str(err))
        return -1

    try:
        latest = COLLECTION_NAME_PREFIX + "latest"
        print("alias index '%s' to %s" % (collection_name, latest))
        aliased_collection = { "collection_name": collection_name }
        client.aliases.upsert(latest, aliased_collection)
    except typesense.exceptions.TypesenseClientError as err:
        print("Cannot build index: ", str(err))
        return -2

    try:
        for collection in client.collections.retrieve():
            if collection["name"] == collection_name:
                continue;

            if collection["name"].startswith(COLLECTION_NAME_PREFIX):
                print("delete collection '%s'" % collection["name"])
                client.collections[collection["name"]].delete()
            else:
                print("ignore collection '%s'" % collection["name"])

    except typesense.exceptions.ObjectNotFound:
        print("Failed to delete collection '%s'.", str(err))

    return 0



def build(client, collection_name):

    schema = {
        'name': collection_name,
        'fields': [
          {
            'name':  'combined',
            'type':  'string'
          },
          {
            'name':  'score',
            'type':  'int32'
          },
        ],
        'default_sorting_field': 'score'
    }


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
                    client.collections[collection_name].documents.import_(documents)
                    documents = []

                if i and i % 100000 == 0:
                    print(i)

            if documents:
                client.collections[collection_name].documents.import_(documents)


    print("indexing complete. waiting for background tasks to finish.")
    sys.stdout.flush()
    time.sleep(5)
