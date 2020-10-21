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
                'artist_credit_name', '[artist_credit_mbids]', 'original_recording_mbid', 'year']

    def fetch(self, params, offset=-1, count=-1):

        mbids = [p['[recording_mbid]'] for p in params]
        with psycopg2.connect(current_app.config['MB_DATABASE_URI']) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:

                # First lookup and MBIDs that may have been redirected
                query = '''SELECT rgr.gid::TEXT AS recording_mbid_old,
                                  r.gid::TEXT AS recording_mbid_new
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
                    redirect_index[r['recording_mbid_old']] = r['recording_mbid_new']

                # Now start looking up actual recordings
                for i, mbid in enumerate(mbids):
                    if mbid in redirect_index:
                        mbids[i] = redirect_index[mbid]

                query = '''SELECT r.gid::TEXT AS recording_mbid, r.name AS recording_name, r.length, r.comment,
                                  ac.id AS artist_credit_id, ac.name AS artist_credit_name,
                                  array_agg(a.gid)::TEXT[] AS artist_credit_mbids,
                                  first_release_date_year AS year
                             FROM recording r
                             JOIN artist_credit ac
                               ON r.artist_credit = ac.id
                             JOIN artist_credit_name acn
                               ON ac.id = acn.artist_credit
                             JOIN artist a
                               ON acn.artist = a.id
                             JOIN track t
                               ON t.recording = r.id
                             JOIN medium m
                               ON t.medium = m.id
                             JOIN release rl
                               ON m.release = rl.id
                             JOIN release_group rg
                               ON rl.release_group = rg.id
                             JOIN release_group_meta rgm
                               ON rg.id = rgm.id
                            WHERE r.gid
                               IN %s
                         GROUP BY r.gid, r.id, r.name, r.length, r.comment, ac.id, ac.name, rgm.first_release_date_year
                         ORDER BY r.gid'''

                args = [tuple([psycopg2.extensions.adapt(p) for p in mbids])]
                curs.execute(query, tuple(args))

                # Build an index of all the fetched recordings
                recording_index = {}
                while True:
                    row = curs.fetchone()
                    if not row:
                        break

                    recording_index[row['recording_mbid']] = dict(row)

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
                            out = dict.fromkeys(self.outputs(), None)
                            out['original_recording_mbid'] = mbid
                            output.append(out)
                            continue

                    r['[artist_credit_mbids]'] = list(set(r['artist_credit_mbids']))
                    del r['artist_credit_mbids']
                    r['original_recording_mbid'] = mbid
                    output.append(r)

                # Ideally offset and count should be handled by the postgres query itself, but the 1:1 relationship
                # of what the user requests and what we need to fetch is no longer true, so we can't easily use LIMIT/OFFSET.
                # We might be able to use a RIGHT JOIN to fix this, but for now I'm happy to leave this as it. We need to
                # revisit this when we get closer to pushing recommendation tools to production.
                if offset > 0 and count > 0:
                    return output[offset:offset+count]

                if offset > 0 and count < 0:
                    return output[offset:]

                if offset < 0 and count > 0:
                    return output[:count]

                return output
