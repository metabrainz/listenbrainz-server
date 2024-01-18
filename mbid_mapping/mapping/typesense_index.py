import re
import time
import datetime

import typesense
import typesense.exceptions
from unidecode import unidecode
import psycopg2

import config
from mapping.utils import log


BATCH_SIZE = 5000


def prepare_string(text):
    return unidecode(re.sub(" +", " ", re.sub(r'[^\w ]+', '', text)).lower())


def build_index(collection_name_prefix, table, combiner):

    client = typesense.Client({
        'nodes': [{
          'host': config.TYPESENSE_HOST,
          'port': config.TYPESENSE_PORT,
          'protocol': 'http',
        }],
        'api_key': config.TYPESENSE_API_KEY,
        'connection_timeout_seconds': 1000000
    })

    collection_name = collection_name_prefix + datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    try:
        log("typesense index: build index '%s'" % collection_name)
        build(client, collection_name, table, combiner)
    except typesense.exceptions.TypesenseClientError as err:
        log("typesense index: Cannot build index: ", str(err))
        return -1

    try:
        latest = collection_name_prefix + "latest"
        log("typesense index: alias index '%s' to %s" % (collection_name, latest))
        aliased_collection = {"collection_name": collection_name}
        client.aliases.upsert(latest, aliased_collection)
    except typesense.exceptions.TypesenseClientError as err:
        log("typesense index: Cannot build index: ", str(err))
        return -2

    try:
        for collection in client.collections.retrieve():
            if collection["name"] == collection_name:
                continue

            if collection["name"].startswith(collection_name_prefix):
                log("typesense index: delete collection '%s'" % collection["name"])
                client.collections[collection["name"]].delete()
            else:
                log("typesense index: ignore collection '%s'" % collection["name"])

    except typesense.exceptions.ObjectNotFound as err:
        log("typesense index: Failed to delete collection '%s'.", str(err))

    return 0


def build(client, collection_name, table, combiner):

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

    with psycopg2.connect(config.SQLALCHEMY_TIMESCALE_URI) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:

            curs.execute(f"SELECT max(score) FROM {table}")
            max_score = curs.fetchone()[0]

            query = f"""
                SELECT recording_name
                     , recording_mbid
                     , release_name
                     , release_mbid
                     , artist_credit_id
                     , artist_credit_name
                     , artist_mbids
                     , score
                  FROM {table}
            """

            curs.execute(query)
            documents = []
            for i, row in enumerate(curs):
                document = dict(row)
                document['artist_mbids'] = "{" + row["artist_mbids"][1:-1] + "}"
                document['score'] = max_score - document['score']
                document['combined'] = prepare_string(combiner(document))
                documents.append(document)

                if len(documents) == BATCH_SIZE:
                    client.collections[collection_name].documents.import_(documents)
                    documents = []

                if i and i % 1000000 == 0:
                    log("typesense index: Indexed %d rows" % i)

            if documents:
                client.collections[collection_name].documents.import_(documents)

    log("typesense index: indexing complete. waiting for background tasks to finish.")
    time.sleep(5)


def build_all():
    def combine_artist_recording(document):
        return document['recording_name'] + " " + document['artist_credit_name']

    def combine_artist_recording_release(document):
        return document['recording_name'] + " " + document['artist_credit_name'] + " " + document['release_name']

    build_index("canonical_musicbrainz_data_", "mapping.canonical_musicbrainz_data", combine_artist_recording)
    build_index("canonical_musicbrainz_data_release_", "mapping.canonical_musicbrainz_data_release_support", combine_artist_recording_release)

