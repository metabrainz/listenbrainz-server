import psycopg2
from flask import current_app
from psycopg2.extras import execute_values


def _resolve_mbids_helper(curs, query, mbids):
    """ Helper to extract common code for resolving redirect and canonical mbids """
    execute_values(curs, query, [(mbid,) for mbid in mbids], page_size=len(mbids))

    index, inverse_index = {}, {}
    for row in curs.fetchall():
        old_mbid = row[0]
        new_mbid = row[1]
        index[old_mbid] = new_mbid
        inverse_index[new_mbid] = old_mbid

    new_mbids = []
    for mbid in mbids:
        # redirect the mbid to find the new recording if one exists otherwise use the original mbid itself
        new_mbids.append(index.get(mbid, mbid))

    return new_mbids, index, inverse_index


def resolve_redirect_mbids(curs, mbids):
    """ Given a list of mbids, resolve redirects if any and return the list of new mbids, a dict of
    redirected mbids and a reverse index of the same.
    """
    query = """
          WITH mbids (gid) AS (VALUES %s)
        SELECT rgr.gid::TEXT AS old
             , r.gid::TEXT AS new
          FROM recording_gid_redirect rgr
          JOIN mbids m
            ON rgr.gid = m.gid::UUID
          JOIN recording r
            ON r.id = rgr.new_id
    """
    return _resolve_mbids_helper(curs, query, mbids)


def resolve_canonical_mbids(curs, mbids):
    """ Check the list of mbids for canonical redirects and return list of canonical mbids.

    Args:
        mbids: list of mbids to check for canonical mbids

    Returns:
        tuple of (list of canonical mbids, dict of redirected mbids as key and the canonical mbid
        replacing it as value, dict of canonical mbids as key and redirected mbids as value)
    """
    query = """
          WITH mbids (gid) AS (VALUES %s)
        SELECT recording_mbid::TEXT AS old
             , canonical_recording_mbid::TEXT AS new
          FROM mapping.canonical_recording_redirect
          JOIN mbids
            ON recording_mbid = gid::UUID
    """
    return _resolve_mbids_helper(curs, query, mbids)


def get_recordings_from_mbids(mbids):
    """ Given a list of recording mbids, resolve redirects if any and return metadata for all recordings """
    with psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as conn,\
            conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
        # First lookup and MBIDs that may have been redirected
        redirected_mbids, index, inverse_index = resolve_redirect_mbids(curs, mbids)

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

        args = [tuple([psycopg2.extensions.adapt(p) for p in redirected_mbids])]
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
                    r = dict(recording_index[index[mbid]])
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
            r['original_recording_mbid'] = inverse_index.get(mbid, mbid)
            output.append(r)
    return output
