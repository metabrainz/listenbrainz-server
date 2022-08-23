#!/usr/bin/env python3

import re

import psycopg2
import psycopg2.extras
from datasethoster import Query
from unidecode import unidecode
from listenbrainz import config


class ArtistCreditRecordingLookupQuery(Query):

    def __init__(self, debug=False):
        self.debug = debug
        self.log_lines = []

    def names(self):
        return ("acr-lookup", "MusicBrainz Artist Credit Recording lookup")

    def inputs(self):
        return ['[artist_credit_name]', '[recording_name]']

    def introduction(self):
        return """This lookup performs an semi-exact string match on Artist Credit and Recording. The given parameters will have non-word
                  characters removed, unaccented and lower cased before being looked up in the database."""

    def outputs(self):
        return ['index', 'artist_credit_arg', 'recording_arg',
                'artist_credit_name', 'release_name', 'recording_name',
                'artist_credit_id', 'artist_mbids', 'release_mbid', 'recording_mbid', 'year']

    def get_debug_log_lines(self):
        lines = self.log_lines
        self.log_lines = []
        return lines

    def fetch(self, params, offset=-1, count=-1):
        lookup_strings = []
        string_index = {}
        for i, param in enumerate(params):
            cleaned = unidecode(re.sub(
                r'[^\w]+', '', param["[artist_credit_name]"] + param["[recording_name]"]).lower())
            lookup_strings.append(cleaned)
            string_index[cleaned] = i

        lookup_strings = tuple(lookup_strings)

        with psycopg2.connect(config.SQLALCHEMY_TIMESCALE_URI) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
                curs.execute("""SELECT artist_credit_name,
                                       artist_credit_id,
                                       artist_mbids::TEXT[],
                                       release_name,
                                       release_mbid,
                                       recording_name,
                                       recording_mbid::TEXT,
                                       year,
                                       combined_lookup
                                  FROM mapping.canonical_musicbrainz_data
                                 WHERE combined_lookup IN %s""", (lookup_strings,))

                results = []
                while True:
                    data = curs.fetchone()
                    if not data:
                        break

                    data = dict(data)
                    index = string_index[data["combined_lookup"]]
                    data["recording_arg"] = params[index]["[recording_name]"]
                    data["artist_credit_arg"] = params[index]["[artist_credit_name]"]
                    data["index"] = index
                    results.append(data)

                    if self.debug:
                        self.log_lines.append(
                            "exact match: '%s' '%s' %s" %
                            (data['artist_credit_name'],
                             data['recording_name'],
                             data['recording_mbid']))

                return results
