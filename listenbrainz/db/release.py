from typing import Iterable

from psycopg2.extras import execute_values
from listenbrainz.db.musicbrainz_entity import _resolve_mbids_helper, resolve_redirect_mbids


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
        SELECT release_mbid::TEXT AS old
             , canonical_release_mbid::TEXT AS new
          FROM mapping.canonical_release_redirect
          JOIN mbids
            ON release_mbid = gid::UUID
    """
    return _resolve_mbids_helper(curs, query, mbids)


def load_releases_from_mbids(ts_curs, mbids: Iterable[str]) -> dict:
    """ Given a list of mbids return a map with mbid as key and the release info as value.


    TODO: Ideally, we should always resolve redirects but that makes testing some LB features difficult
        because we don't have a MB db in the test environment yet. Once, we do we can merge the two versions.
    """
    if not mbids:
        return {}

    query = """
        SELECT mbc.release_mbid::TEXT
             , artist_mbids::TEXT[]
             , artist_data->>'name' AS artist
             , release_data->>'name' AS title
             , (release_data->>'caa_id')::bigint AS caa_id
             , release_data->>'caa_release_mbid' AS caa_release_mbid
             , array_agg(artist->>'name' ORDER BY position) AS ac_names
             , array_agg(artist->>'join_phrase' ORDER BY position) AS ac_join_phrases
          FROM (VALUES %s) AS m (release_mbid)
          JOIN mapping.mb_metadata_cache mbc
            ON mbc.release_mbid = m.release_mbid::uuid
  JOIN LATERAL jsonb_array_elements(artist_data->'artists') WITH ORDINALITY artists(artist, position)
            ON TRUE
      GROUP BY mbc.release_mbid
             , artist_mbids
             , artist_data->>'name'
             , artist_data->>'artist_credit_id'
             , release_data->>'name'
             , release_data->>'year'
             , release_data->>'caa_id'
             , release_data->>'caa_release_mbid'
    """
    results = execute_values(ts_curs, query, [(mbid,) for mbid in mbids], fetch=True)
    rows = {}
    for row in results:
        data = dict(row)
        release_mbid = data["release_mbid"]

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
        rows[release_mbid] = data

    return rows


def load_releases_from_mbids_with_redirects(mb_curs, ts_curs, mbids):
    """ Given a list of release mbids, resolve redirects if any and return metadata for all releases """
    redirected_mbids, index, inverse_index = resolve_redirect_mbids(mb_curs, "release", mbids)
    release_index = load_releases_from_mbids(ts_curs, redirected_mbids)
    _, canonical_index, _ = resolve_canonical_mbids(ts_curs, redirected_mbids)

    # Finally collate all the results, ensuring that we have one entry with original_release_mbid for each input
    output = []
    for mbid in mbids:
        redirected_mbid = index.get(mbid, mbid)
        if redirected_mbid in release_index:
            data = release_index[redirected_mbid]
            r = {
                "release_mbid": redirected_mbid,
                "release_name": data["title"],
                "release_year": data["year"],
                "artist_credit_id": data["artist_credit_id"],
                "artist_credit_name": data["artist"],
                "[artist_credit_mbids]": data["artist_mbids"],
                "caa_id": data["caa_id"],
                "caa_release_mbid": data["caa_release_mbid"],
                "artists": data["artists"],
                "original_release_mbid": mbid,
                "canonical_release_mbid": canonical_index.get(redirected_mbid, redirected_mbid)
            }
        else:
            r = {
                'release_mbid': None,
                'release_name': None,
                'release_year': None,
                'artist_credit_id': None,
                'artist_credit_name': None,
                '[artist_credit_mbids]': None,
                'caa_id': None,
                'caa_release_mbid': None,
                'artists': [],
                'canonical_release_mbid': None,
                'original_release_mbid': mbid
            }
        output.append(r)
    return output
