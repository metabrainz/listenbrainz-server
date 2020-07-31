from operator import itemgetter

import psycopg2
import psycopg2.extras
from flask import current_app
from datasethoster import Query


class ArtistCreditIdFromArtistMBIDQuery(Query):

    def names(self):
        return ("artist-credit-from-artist-mbid", "MusicBrainz Artist Credit From Artist MBID")

    def inputs(self):
        return ['artist_mbid']

    def introduction(self):
        return """Look up all available artist credit ids from an artist mbid."""

    def outputs(self):
        return ['artist_mbid', 'artist_credit_id']

    def fetch(self, params, offset=-1, limit=-1):

        with psycopg2.connect(current_app.config['MB_DATABASE_URI']) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:

                acs = tuple([ p['artist_mbid'] for p in params ])
                curs.execute("""SELECT a.gid AS artist_mbid, 
                                       array_agg(ac.id) AS artist_credit_ids
                                  FROM artist_credit ac 
                                  JOIN artist_credit_name acn 
                                    ON ac.id = acn.artist_credit 
                                  JOIN artist a 
                                    ON acn.artist = a.id 
                                 WHERE a.gid in %s
                              GROUP BY a.gid 
                              """, (acs,))
                output = []
                while True:
                    row = curs.fetchone()
                    if not row:
                        break

                    output.append(dict(row))

                return output
