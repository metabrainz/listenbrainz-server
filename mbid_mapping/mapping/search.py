
import typesense
import typesense.exceptions
from mapping.typesense_index import prepare_string

import config


def search(query):

    client = typesense.Client({
        'nodes': [{
          'host': config.TYPESENSE_HOST,
          'port': config.TYPESENSE_PORT,
          'protocol': 'http',
        }],
        'api_key': config.TYPESENSE_API_KEY,
        'connection_timeout_seconds': 2
    })

    search_parameters = {
        'q': prepare_string(query),
        'query_by': "combined",
        'prefix': 'no',
        'num_typos': 5
    }

    hits = client.collections['canonical_musicbrainz_data_latest'].documents.search(search_parameters)

    output = []
    for hit in hits['hits']:
        output.append({'artist_credit_name': hit['document']['artist_credit_name'],
                       'artist_mbids': hit['document']['artist_mbids'],
                       'release_name': hit['document']['release_name'],
                       'release_mbid': hit['document']['release_mbid'],
                       'recording_name': hit['document']['recording_name'],
                       'recording_mbid': hit['document']['recording_mbid']})

    return output
