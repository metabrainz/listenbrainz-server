#!/usr/bin/env python3

import re

from flask import current_app
import psycopg2
import psycopg2.extras
from datasethoster import Query
from unidecode import unidecode
from listenbrainz import config


class RecordingYearLookupQuery(Query):

    def names(self):
        return ("recording-year-lookup", "MusicBrainz Recording Year lookup")

    def inputs(self):
        return ['[artist_credit_name]', '[recording_name]']

    def introduction(self):
        return """Given an artist_credit_name and a recording name, try and find the first release
                  year of that release in MusicBrainz."""

    def outputs(self):
        return ['artist_credit_name', 'recording_name', 'year']

    def fetch(self, params, offset=-1, count=-1):
        artists = []
        recordings = []
        for param in params:
            recording = unidecode(re.sub(r'\W+', '', param['[recording_name]'].lower()))
            artist = unidecode(re.sub(r'\W+', '', param['[artist_credit_name]'].lower()))
            artists.append(artist)
            recordings.append(recording)

        artists = tuple(artists)
        recordings = tuple(recordings)

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
                    recording = unidecode(re.sub(r'\W+', '', param['[recording_name]'].lower()))
                    artist = unidecode(re.sub(r'\W+', '', param['[artist_credit_name]'].lower()))
                    try:
                        results.append({ 
                                         'artist_credit_name': param['[artist_credit_name]'], 
                                         'recording_name': param['[recording_name]'], 
                                         'year': index[artist+recording] 
                                       })
                    except KeyError:
                        pass

                return results
