#!/usr/bin/env python3

import psycopg2
import psycopg2.extras
from datasethoster import Query
from unidecode import unidecode

import config


class ArtistCreditRecordingLookupQuery(Query):

    def names(self):
        return ("acr-lookup", "MusicBrainz Artist Credit Recording lookup")

    def inputs(self):
        return ['artist_credit_name', 'recording_name']

    def introduction(self):
        return """This lookup performs an semi-exact string match on Artist Credit and Recording. The given parameters will have non-word
                  characters removed, unaccted and lower cased before being looked up in the database."""

    def outputs(self):
        return ['artist_credit_name', 'release_name', 'recording_name', 
                'artist_credit_id', 'release_mbid', 'recording_mbid']

    def fetch(self, params, offset=-1, count=-1):
        artists = []
        recordings = []
        for param in params:
            artists.append("".join(unidecode(param['artist_credit_name'].lower()).split()))
            recordings.append("".join(unidecode(param['recording_name'].lower()).split()))
        artists = tuple(artists)
        recordings = tuple(recordings)

        with psycopg2.connect(config.DB_CONNECT_MB) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
                curs.execute("""SELECT DISTINCT ac.name AS artist_credit_name, 
                                       rl.name AS release_name, 
                                       r.name AS recording_name,
                                       rl.gid AS release_mbid,
                                       r.gid AS recording_mbid,
                                       artist_credit_id
                                  FROM mapping.recording_artist_credit_pairs
                                  JOIN recording r
                                    ON r.id = recording_id
                                  JOIN release rl
                                    ON rl.id = release_id
                                  JOIN artist_credit ac
                                    ON r.artist_credit = ac.id
                                 WHERE artist_credit_name IN %s
                                   AND recording_name IN %s""", (artists, recordings))

                results = []
                while True:
                    data = curs.fetchone()
                    if not data:
                        break

                    results.append(dict(data))

                return results
