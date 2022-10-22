import psycopg2
from flask import current_app


def get_recordings_from_mbids(mbids):
    """ Given a list of recording mbids, resolve redirects if any and return metadata for all recordings """
    with psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as conn:
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
            inverse_redirect_index = {}
            while True:
                row = curs.fetchone()
                if not row:
                    break

                r = dict(row)
                redirect_index[r['recording_mbid_old']] = r['recording_mbid_new']
                inverse_redirect_index[r['recording_mbid_new']] = r['recording_mbid_old']

            # Now start looking up actual recordings
            for i, mbid in enumerate(mbids):
                if mbid in redirect_index:
                    mbids[i] = redirect_index[mbid]

            query = '''SELECT r.gid::TEXT AS recording_mbid,
                              r.name AS recording_name,
                              r.length,
                              r.comment,
                              ac.id AS artist_credit_id,
                              ac.name AS artist_credit_name,
                              array_agg(a.gid ORDER BY acn.position)::TEXT[] AS artist_credit_mbids
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
            for mbid in mbids:
                try:
                    r = dict(recording_index[mbid])
                except KeyError:
                    try:
                        r = dict(recording_index[redirect_index[mbid]])
                    except KeyError:
                        output.append({'recording_mbid': None,
                                       'recording_name': None,
                                       'length': None,
                                       'comment': None,
                                       'artist_credit_id': None,
                                       'artist_credit_name': None,
                                       '[artist_credit_mbids]': None,
                                       'original_recording_mbid': mbid})
                        continue

                r['[artist_credit_mbids]'] = [ac_mbid for ac_mbid in r['artist_credit_mbids']]
                del r['artist_credit_mbids']
                r['original_recording_mbid'] = inverse_redirect_index.get(mbid, mbid)
                output.append(r)
    return output
