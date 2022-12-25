import psycopg2
from psycopg2.extras import execute_values
from psycopg2.sql import SQL, Identifier

from listenbrainz.db.msid_mbid_mapping import load_recordings_from_mbids


def _resolve_mbids_helper(curs, query, mbids):
    """ Helper to extract common code for resolving redirect and canonical mbids """
    result = execute_values(curs, query, [(mbid,) for mbid in mbids], fetch=True)
    index, inverse_index = {}, {}
    for row in result:
        old_mbid = row[0]
        new_mbid = row[1]
        index[old_mbid] = new_mbid
        inverse_index[new_mbid] = old_mbid

    new_mbids = []
    for mbid in mbids:
        # redirect the mbid to find the new recording if one exists otherwise use the original mbid itself
        new_mbids.append(index.get(mbid, mbid))

    return new_mbids, index, inverse_index


def resolve_redirect_mbids(curs, table, mbids):
    """ Given a list of mbids, resolve redirects if any and return the list of new mbids, a dict of
    redirected mbids and a reverse index of the same.
    """
    redirect_table = table + "_gid_redirect"
    query = SQL("""
          WITH mbids (gid) AS (VALUES %s)
        SELECT redirect.gid::TEXT AS old
             , target.gid::TEXT AS new
          FROM {redirect_table} redirect
          JOIN mbids
            ON redirect.gid = mbids.gid::UUID
          JOIN {target_table} target
            ON target.id = redirect.new_id
    """).format(target_table=Identifier(table), redirect_table=Identifier(redirect_table))
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


def get_recordings_from_mbids(mb_curs, ts_curs, mbids):
    """ Given a list of recording mbids, resolve redirects if any and return metadata for all recordings """
    redirected_mbids, index, inverse_index = resolve_redirect_mbids(mb_curs, "recording", mbids)
    recording_index = load_recordings_from_mbids(ts_curs, redirected_mbids)
    _, canonical_index, _ = resolve_canonical_mbids(ts_curs, redirected_mbids)

    # Finally collate all the results, ensuring that we have one entry with original_recording_mbid for each input
    output = []
    for mbid in mbids:
        redirected_mbid = index.get(mbid, mbid)
        if redirected_mbid in recording_index:
            data = recording_index[redirected_mbid]
            r = {
                "recording_mbid": redirected_mbid,
                "recording_name": data["title"],
                "length": data["length"],
                "artist_credit_id": data["artist_credit_id"],
                "artist_credit_name": data["artist"],
                "[artist_credit_mbids]": data["artist_mbids"],
                "caa_id": data["caa_id"],
                "caa_release_mbid": data["caa_release_mbid"],
                "original_recording_mbid": mbid,
                "canonical_recording_mbid": canonical_index.get(redirected_mbid, redirected_mbid)
            }
        else:
            r = {
                'recording_mbid': None,
                'recording_name': None,
                'length': None,
                'artist_credit_id': None,
                'artist_credit_name': None,
                '[artist_credit_mbids]': None,
                'canonical_recording_mbid': None,
                'original_recording_mbid': mbid
            }
        output.append(r)
    return output
