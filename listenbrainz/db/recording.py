from typing import Iterable

from psycopg2.extras import execute_values
from psycopg2.sql import SQL, Identifier


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
    """).format(target_table=Identifier("musicbrainz", table), redirect_table=Identifier("musicbrainz", redirect_table))
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


def load_recordings_from_mbids(ts_curs, mbids: Iterable[str]) -> dict:
    """ Given a list of mbids return a map with mbid as key and the recording info as value.


    TODO: Ideally, we should always resolve redirects but that makes testing some LB features difficult
        because we don't have a MB db in the test environment yet. Once, we do we can merge the two versions.
    """
    if not mbids:
        return {}

    query = """
        SELECT mbc.recording_mbid::TEXT
             , release_mbid::TEXT
             , artist_mbids::TEXT[]
             , artist_data->>'name' AS artist
             , (artist_data->>'artist_credit_id')::bigint AS artist_credit_id
             , recording_data->>'name' AS title
             , (recording_data->>'length')::bigint AS length
             , release_data->>'name' AS release
             , (release_data->>'caa_id')::bigint AS caa_id
             , release_data->>'caa_release_mbid' AS caa_release_mbid
             , array_agg(artist->>'name' ORDER BY position) AS ac_names
             , array_agg(artist->>'join_phrase' ORDER BY position) AS ac_join_phrases
          FROM (VALUES %s) AS m (recording_mbid)
          JOIN mapping.mb_metadata_cache mbc
            ON mbc.recording_mbid = m.recording_mbid::uuid
  JOIN LATERAL jsonb_array_elements(artist_data->'artists') WITH ORDINALITY artists(artist, position)
            ON TRUE
      GROUP BY mbc.recording_mbid
             , release_mbid
             , artist_mbids
             , artist_data->>'name'
             , artist_data->>'artist_credit_id'
             , recording_data->>'name'
             , recording_data->>'length'
             , release_data->>'name'
             , release_data->>'caa_id'
             , release_data->>'caa_release_mbid'
    """
    results = execute_values(ts_curs, query, [(mbid,) for mbid in mbids], fetch=True)
    rows = {}
    for row in results:
        data = dict(row)
        recording_mbid = data["recording_mbid"]

        ac_names = data.pop("ac_names")
        ac_join_phrases = data.pop("ac_join_phrases")

        artists = []
        for (mbid, name, join_phrase) in zip(data["artist_mbids"], ac_names, ac_join_phrases):
            artists.append({
                "artist_mbid": mbid,
                "artist_credit_name": name,
                "join_phrase": join_phrase
            })
        data["artists"] = artists
        rows[recording_mbid] = data

    return rows


def load_recordings_from_mbids_with_redirects(mb_curs, ts_curs, mbids):
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
                "artist_credit_mbids": data["artist_mbids"],
                "release_name": data["release"],
                "release_mbid": data["release_mbid"],
                "caa_id": data["caa_id"],
                "caa_release_mbid": data["caa_release_mbid"],
                "artists": data["artists"],
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
                'artist_credit_mbids': None,
                'release_name': None,
                'release_mbid': None,
                'caa_id': None,
                'caa_release_mbid': None,
                'artists': [],
                'canonical_recording_mbid': None,
                'original_recording_mbid': mbid
            }
        output.append(r)
    return output
