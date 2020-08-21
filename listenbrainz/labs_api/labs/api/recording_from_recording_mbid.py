import sys
import uuid

import psycopg2
import psycopg2.extras
from flask import current_app
from datasethoster import Query
from datasethoster.main import app, register_query

psycopg2.extras.register_uuid()

class RecordingFromRecordingMBIDQuery(Query):
    '''
        Look up a musicbrainz data for a list of recordings, based on MBID. 
    '''

    def names(self):
        return ("recording-mbid-lookup", "MusicBrainz Recording by MBID Lookup")

    def inputs(self):
        return ['recording_mbid']

    def introduction(self):
        return """Look up recording and artist information given a recording MBID"""

    def outputs(self):
        return ['recording_mbid', 'recording_name', 'length', 'comment', 
                'artist_credit_id', 'artist_credit_name', '[artist_credit_mbids]']

    def fetch(self, params, offset=-1, count=-1):

        mbids = tuple([ psycopg2.extensions.adapt(p['recording_mbid']) for p in params ])
        with psycopg2.connect(current_app.config['MB_DATABASE_URI']) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
                query = '''SELECT r.gid AS recording_mbid, r.name AS recording_name, r.length, r.comment, 
                                  ac.id AS artist_credit_id, ac.name AS artist_credit_name, 
                                  array_agg(a.gid) AS artist_credit_mbids
                             FROM recording r
                             JOIN artist_credit ac 
                               ON r.artist_credit = ac.id
                             JOIN artist_credit_name acn
                               ON ac.id = acn.artist_credit
                             JOIN artist a
                               ON acn.artist = a.id
                            WHERE r.gid 
                               IN %s
                         GROUP BY r.gid, r.id, r.name, r.length, r.comment, ac.id, ac.name
                         ORDER BY r.gid'''

                args = [mbids]
                if count > 0:
                    query += " LIMIT %s"
                    args.append(count)
                if offset >= 0:
                    query += " OFFSET %s"
                    args.append(offset)

                curs.execute(query, tuple(args))

                output = []
                while True:
                    row = curs.fetchone()
                    if not row:
                        break

                    r = dict(row)
                    r['recording_mbid'] = str(r['recording_mbid'])
                    r['[artist_credit_mbids]'] = [ str(r) for r in r['artist_credit_mbids'] ]
                    del r['artist_credit_mbids']
                    output.append(r)

        return output
