import ujson

import typesense
import typesense.exceptions
from datasethoster import Query
from datasethoster.main import register_query
from unidecode import unidecode

from listenbrainz import config
from listenbrainz.labs_api.labs.api.mbid_mapping import prepare_query, COLLECTION_NAME

NUM_TYPOS = 5


class RecordingSearchQuery(Query):
    """
        Carry out a recording search suitable for end-users to enter a mix of artist and recording name in hopes
        of finding the right track. Since this endpoint is end-user facing, it supports only one query per call.

        For best results, the query field should be "artist_credit_name + recording_name", but that is not super important.
    """

    def __init__(self):
        self.debug = False

        self.client = typesense.Client({
            'nodes': [{
                'host': config.TYPESENSE_HOST,
                'port': config.TYPESENSE_PORT,
                'protocol': 'http',
            }],
            'api_key': config.TYPESENSE_API_KEY,
            'connection_timeout_seconds': 2
        })

    def names(self):
        return ("recording-search", "MusicBrainz Recording search")

    def inputs(self):
        return ['query']

    def introduction(self):
        return """This page allows you to enter the name of an artist and the name of a recording (track)
                  and the query will attempt to find a (potentially fuzzy) match in MusicBrainz. Construct
                  the search query by combining artist name and recording name. (e.g. 'portishead strangers')"""

    def outputs(self):
        return ['recording_name', 'recording_mbid',
                'release_name', 'release_mbid',
                'artist_credit_name', 'artist_credit_id']

    def fetch(self, params, offset=-1, count=-1):

        search_parameters = {
            'q': prepare_query(params[0]['query']),
            'query_by': "combined",
            'prefix': 'no',
            'num_typos': NUM_TYPOS
        }

        hits = self.client.collections[COLLECTION_NAME].documents.search(
            search_parameters)

        output = []
        for hit in hits['hits']:
            output.append({'artist_credit_name': hit['document']['artist_credit_name'],
                           'artist_credit_id': hit['document']['artist_credit_id'],
                           'release_name': hit['document']['release_name'],
                           'release_mbid': hit['document']['release_mbid'],
                           'recording_name': hit['document']['recording_name'],
                           'recording_mbid': hit['document']['recording_mbid']})

        return output
