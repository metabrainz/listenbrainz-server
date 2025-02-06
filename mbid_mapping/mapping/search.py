
from pyxdameraulevenshtein import damerau_levenshtein_distance_seqs
import typesense
import typesense.exceptions
from mapping.typesense_index import prepare_string, prepare_string_v2

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


def mf_search(max_len, collection, artist_name, recording_name):

    client = typesense.Client({
        'nodes': [{
          'host': config.TYPESENSE_HOST,
          'port': config.TYPESENSE_PORT,
          'protocol': 'http',
        }],
        'api_key': config.TYPESENSE_API_KEY,
        'connection_timeout_seconds': 2
    })

    artist_p, artist_p_rem = prepare_string_v2(artist_name, max_len)
    recording_p, recording_p_rem = prepare_string_v2(recording_name, max_len)

    # not specifying num typos will default to 2 typos per field, which is sane
    search_parameters = {
        'q': artist_p + " " + recording_p,
        'query_by': "artist,recording",
        'prefix': 'no',
    }

    hits = client.collections[collection].documents.search(search_parameters)

    artist_hits = []
    recording_hits = []
    for hit in hits['hits']:
        artist_hits.append(hit['document']['artist'] + hit['document']['artist_rem'])
        recording_hits.append(hit['document']['recording'] + hit['document']['track_rem'])
    
    artist_dists = damerau_levenshtein_distance_seqs(artist_p + artist_p_rem, artist_hits)
    recording_dists = damerau_levenshtein_distance_seqs(recording_p + recording_p_rem, recording_hits)

    output = []
    for i, hit in enumerate(hits['hits']):
        output.append({'artist_name': hit['document']['artist'] + hit['document']['artist_rem'],
                       'recording_name': hit['document']['recording'] + hit['document']['track_rem'],
                       'dist': artist_dists[i] + recording_dists[i]})

    return sorted(output, key=lambda a: a['dist'])
