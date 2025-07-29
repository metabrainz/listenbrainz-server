from typing import Iterable

from psycopg2.extras import DictCursor, execute_values
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
             , tag_data->'recording' AS tags
          FROM (VALUES %s) AS m (recording_mbid)
          JOIN mapping.mb_metadata_cache mbc
            ON mbc.recording_mbid = m.recording_mbid::uuid
  JOIN LATERAL jsonb_array_elements(artist_data->'artists') WITH ORDINALITY artists(artist, position)
            ON TRUE
      GROUP BY mbc.recording_mbid
             , tag_data->'recording'
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
                "tags": data["tags"],
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
                'tags': [],
                'canonical_recording_mbid': None,
                'original_recording_mbid': mbid
            }
        output.append(r)
    return output


def load_release_groups_for_recordings(mb_curs: DictCursor, mbids: Iterable[str]) -> dict:
    """
    Given a list of recording MBIDs, return a map with recording MBID as key
    and the release group MBID as value.
    """
    query = """
        WITH input_mbids AS (
            SELECT unnest(%s::uuid[]) AS gid
        ),
        target_rg AS (
            SELECT DISTINCT rg.id
            FROM musicbrainz.recording rec
            JOIN input_mbids mb ON mb.gid = rec.gid
            JOIN musicbrainz.track t ON t.recording = rec.id
            JOIN musicbrainz.medium m ON m.id = t.medium
            JOIN musicbrainz.release r ON r.id = m.release
            JOIN musicbrainz.release_group rg ON rg.id = r.release_group
        ),
        artist_credits AS (
            SELECT
                rg.id AS release_group_id,
                ac.name AS artist_credit_name,
                array_agg(a.gid::text ORDER BY acn.position) AS artist_credit_mbids,
                jsonb_agg(
                    jsonb_build_object(
                        'artist_credit_name', acn.name,
                        'join_phrase', acn.join_phrase,
                        'artist_mbid', a.gid::TEXT
                    )
                    ORDER BY acn.position
                ) AS artists
            FROM musicbrainz.release_group rg
            JOIN musicbrainz.artist_credit ac ON ac.id = rg.artist_credit
            JOIN musicbrainz.artist_credit_name acn ON acn.artist_credit = ac.id
            JOIN musicbrainz.artist a ON a.id = acn.artist
            WHERE rg.id IN (SELECT id FROM target_rg)
            GROUP BY rg.id, ac.name
        ),
        rg_cover_art AS (
            SELECT DISTINCT ON (rg.id)
                rg.id AS release_group,
                caa.id AS caa_id,
                caa_rel.gid AS caa_release_mbid
            FROM musicbrainz.release_group rg
            JOIN musicbrainz.release caa_rel ON rg.id = caa_rel.release_group
            LEFT JOIN (
                SELECT release, date_year, date_month, date_day
                FROM musicbrainz.release_country
                UNION ALL
                SELECT release, date_year, date_month, date_day
                FROM musicbrainz.release_unknown_country
            ) re ON re.release = caa_rel.id
            FULL JOIN cover_art_archive.release_group_cover_art rgca
                ON rgca.release = caa_rel.id
            LEFT JOIN cover_art_archive.cover_art caa
                ON caa.release = caa_rel.id
            LEFT JOIN cover_art_archive.cover_art_type cat
                ON cat.id = caa.id
            WHERE rg.id IN (SELECT id FROM target_rg)
              AND type_id = 1
              AND mime_type != 'application/pdf'
            ORDER BY rg.id, rgca.release, re.date_year, re.date_month, re.date_day, caa.ordering
        )
        SELECT
            rg.gid::text AS mbid,
            rg.name AS name,
            rgpm.name AS type,
            array_agg(DISTINCT rgst.name) AS secondary_types,
            ac.artist_credit_name,
            ac.artist_credit_mbids,
            make_date(
                rgm.first_release_date_year,
                rgm.first_release_date_month,
                rgm.first_release_date_day
            ) AS date,
            rgca.caa_id,
            rgca.caa_release_mbid::text,
            ac.artists
        FROM target_rg trg
        JOIN musicbrainz.release_group rg ON rg.id = trg.id
        JOIN musicbrainz.release_group_primary_type rgpm ON rgpm.id = rg.type
        LEFT JOIN musicbrainz.release_group_secondary_type_join rgstj ON rgstj.release_group = rg.id
        LEFT JOIN musicbrainz.release_group_secondary_type rgst ON rgst.id = rgstj.secondary_type
        JOIN artist_credits ac ON ac.release_group_id = rg.id
        JOIN musicbrainz.release_group_meta rgm ON rgm.id = rg.id
        LEFT JOIN rg_cover_art rgca ON rgca.release_group = rg.id
        GROUP BY
            rg.id,
            rg.name,
            rg.gid,
            rgpm.name,
            ac.artist_credit_name,
            ac.artist_credit_mbids,
            make_date(
                rgm.first_release_date_year,
                rgm.first_release_date_month,
                rgm.first_release_date_day
            ),
            rgca.caa_id,
            rgca.caa_release_mbid,
            ac.artists;
    """

    mbid_array = list(mbids)
    mb_curs.execute(query, (mbid_array,))
    results = mb_curs.fetchall()
    return {row["mbid"]: dict(row) for row in results}
