#!/usr/bin/env python3

import re

from flask import current_app
import psycopg2
import psycopg2.extras
from datasethoster import Query
from unidecode import unidecode
from listenbrainz import config


class YearFromArtistCreditRecordingQuery(Query):
    """ 
        Lookup year from artist_credit_name and recording name. The main goal of this lookup
        is to enable year lookups in troi as a step after recording metadata lookup. If the
        metadata hasn't been looked up in MB and it doesn't exactly match what is in MB,
        then this query will return no results. If a year lookup with more flexiblity is needed
        in the future, then another endpoint will need to be created. This version is catering
        to the needs of troi.
    """

    def names(self):
        return ("year-artist-recording-year-lookup", "MusicBrainz Recording Year lookup")

    def inputs(self):
        return ['[artist_credit_name]', '[recording_name]']

    def introduction(self):
        return """Given an artist_credit_name and a recording name, try and find the first release
                  year of that release in MusicBrainz. This lookup uses an exact string match to find
                  the year, so the metadata must match the data in MusicBrainz exactly."""

    def outputs(self):
        return ['artist_credit_name', 'recording_name', 'year']

    def fetch(self, params, offset=-1, count=-1):
        artists = tuple([ p['[artist_credit_name]'] for p in params ])
        recordings = tuple([ p['[recording_name]'] for p in params ])
        with psycopg2.connect(current_app.config['MB_DATABASE_URI']) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
                curs.execute("""SELECT DISTINCT artist_credit_name, 
                                       recording_name,
                                       year
                                  FROM mapping.year_mapping
                                 WHERE artist_credit_name IN %s
                                   AND recording_name IN %s""", (artists, recordings))

                index = {}
                while True:
                    row = curs.fetchone()
                    if not row:
                        break

                    index[row['artist_credit_name'] + row['recording_name']] = row['year']

                results = []
                for param in params:
                    try:
                        results.append({ 
                                         'artist_credit_name': param['[artist_credit_name]'], 
                                         'recording_name': param['[recording_name]'], 
                                         'year': index[param['[artist_credit_name]']+param['[recording_name]']] 
                                       })
                    except KeyError:
                        pass

                return results
