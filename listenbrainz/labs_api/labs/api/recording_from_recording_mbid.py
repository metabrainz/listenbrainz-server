import copy
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
        return ['[recording_mbid]']

    def introduction(self):
        return """Look up recording and artist information given a recording MBID"""

    def outputs(self):
        return ['recording_mbid', 'recording_name', 'length', 'comment', 'artist_credit_id',
                'artist_credit_name', '[artist_credit_mbids]', 'original_recording_mbid']

    def fetch(self, params, offset=-1, count=-1):

        mbids = [p['[recording_mbid]'] for p in params]
        with psycopg2.connect(current_app.config['MB_DATABASE_URI']) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:

                # First lookup and MBIDs that may have been redirected
                query = '''SELECT rgr.gid AS recording_mbid_old,
                                  r.gid AS recording_mbid_new
                             FROM recording_gid_redirect rgr
                             JOIN recording r
                               ON r.id = rgr.new_id
                            where rgr.gid in %s'''

                args = [tuple([psycopg2.extensions.adapt(p) for p in mbids])]
                curs.execute(query, tuple(args))

                # Build an index with all redirected recordings
                redirect_index = {}
                while True:
                    row = curs.fetchone()
                    if not row:
                        break

                    r = dict(row)
                    redirect_index[str(r['recording_mbid_old'])] = str(r['recording_mbid_new'])

                # Now start looking up actual recordings
                for i, mbid in enumerate(mbids):
                    if mbid in redirect_index:
                        mbids[i] = redirect_index[mbid]

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

                args = [tuple([psycopg2.extensions.adapt(p) for p in mbids])]
                curs.execute(query, tuple(args))

                # Build an index of all the fetched recordings and clean up UUID() -> str
                recording_index = {}
                while True:
                    row = curs.fetchone()
                    if not row:
                        break

                    r = dict(row)
                    mbid = str(r['recording_mbid'])
                    r['recording_mbid'] = mbid
                    recording_index[mbid] = dict(row)

                # Finally collate all the results, ensuring that we have one entry with original_recording_mbid for each 
                # input argument
                output = []
                for p in params:
                    mbid = p['[recording_mbid]'] 
                    try:
                        r = copy.copy(recording_index[mbid])
                    except KeyError:
                        try:
                            r = copy.copy(recording_index[redirect_index[mbid]])
                        except KeyError:
                            out = {} 
                            for k in self.outputs():
                                if k == 'original_recording_mbid':
                                    out['original_recording_mbid'] = mbid
                                else:
                                    out['original_recording_mbid'] = None
                            output.append(out)
                            continue

                    r['[artist_credit_mbids]'] = [str(r) for r in r['artist_credit_mbids']]
                    del r['artist_credit_mbids']
                    r['original_recording_mbid'] = mbid
                    output.append(r)

                if offset > 0 and count > 0:
                    return output[offset:offset+count]

                if offset > 0 and count < 0:
                    return output[offset:]

                if offset < 0 and count > 0:
                    return output[:count]

                return output
