#!/usr/bin/env python3

import re

import psycopg2
import psycopg2.extras
from datasethoster import Query
from unidecode import unidecode

import config


class ArtistCreditRecordingLookupQuery(Query):

    def names(self):
        return ("acr-lookup", "MusicBrainz Artist Credit Recording lookup")

    def inputs(self):
        return ['[artist_credit_name]', '[recording_name]']

    def introduction(self):
        return """This lookup performs an semi-exact string match on Artist Credit and Recording. The given parameters will have non-word
                  characters removed, unaccted and lower cased before being looked up in the database."""

    def outputs(self):
        return ['artist_credit_name', 'release_name', 'recording_name', 
                'artist_credit_id', 'release_mbid', 'recording_mbid']

    def fetch(self, params, offset=-1, count=-1):
        lookup_strings = []
        for param in params:
            lookup_strings.append(unidecode(re.sub(r'[^\w]+', '', param["[artist_credit_name]"] + param["[recording_name]"]).lower()))
        lookup_strings = tuple(lookup_strings)

        with psycopg2.connect(current_app.config['MB_DATABASE_URI']) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
                curs.execute("""SELECT artist_credit_name,
                                       artist_credit_id,
                                       release_name,
                                       release_mbid,
                                       recording_name,
                                       recording_mbid
                                  FROM mapping.mbid_mapping
                                 WHERE combined_lookup IN %s""", (lookup_strings,))

                results = []
                while True:
                    data = curs.fetchone()
                    if not data:
                        break

                    results.append(dict(data))

                return results
