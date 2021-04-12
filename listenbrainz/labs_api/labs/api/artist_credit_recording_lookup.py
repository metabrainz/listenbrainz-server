#!/usr/bin/env python3

import re

import psycopg2
import psycopg2.extras
from datasethoster import Query
from flask import current_app
from unidecode import unidecode


class ArtistCreditRecordingLookupQuery(Query):

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
                'artist_credit_id', 'release_mbid', 'recording_mbid']

    def fetch(self, params, offset=-1, count=-1):
        lookup_strings = []
        string_index = {}
        for i, param in enumerate(params):
            cleaned = unidecode(re.sub(
                r'[^\w]+', '', param["[artist_credit_name]"] + param["[recording_name]"]).lower())
            lookup_strings.append(cleaned)
            string_index[cleaned] = i

        lookup_strings = tuple(lookup_strings)

        with psycopg2.connect(current_app.config['DB_CONNECT_MAPPING']) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
                curs.execute("""SELECT artist_credit_name,
                                       artist_credit_id,
                                       release_name,
                                       release_mbid,
                                       recording_name,
                                       recording_mbid,
                                       combined_lookup
                                  FROM mapping.mbid_mapping
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

                return results
