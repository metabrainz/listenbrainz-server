def get_recording_length_cache_query(with_filter: bool = False):
    """ Import recording lengths from postgres to HDFS for use in year in music and similar entity calculation.

        If with_filter is True, the query is prepared in a way such that it can be filtered using a list of
        recording mbids passed as a VALUES list.
    """
    mbid_filter_clause_r = ""
    mbid_filter_clause_rgr = ""
    cte_clause = ""

    if with_filter:
        cte_clause = "WITH mbids (mbid) AS (VALUES %s)"
        mbid_filter_clause_r = "JOIN mbids m ON m.mbid = r.gid"
        mbid_filter_clause_rgr = "JOIN mbids m ON m.mbid = rgr.gid"

    return f"""
        {cte_clause}
        SELECT r.gid::text AS recording_mbid
             , r.length
             , r.id AS recording_id
             , false AS is_redirect
          FROM musicbrainz.recording r
         {mbid_filter_clause_r}
         UNION ALL
        SELECT rgr.gid::text AS recording_mbid
             , r.length
             , rgr.new_id AS recording_id
             , true AS is_redirect
          FROM musicbrainz.recording_gid_redirect rgr
          JOIN musicbrainz.recording r
            ON rgr.new_id = r.id
         {mbid_filter_clause_rgr}
    """


def get_recording_artist_cache_query(with_filter: bool = False):
    """ Import recording artists from postgres to HDFS for use in periodic jams calculation.

        If with_filter is True, the query is prepared in a way such that it can be filtered using a list of
        recording mbids passed as a VALUES list.
    """
    cte_clause = ""
    mbid_filter_clause = ""
    if with_filter:
        cte_clause = "WITH mbids (mbid) AS (VALUES %s)"
        mbid_filter_clause = "JOIN mbids m ON m.mbid = r.gid"

    return f"""
        {cte_clause}
        SELECT r.gid::text AS recording_mbid
             , array_agg(a.gid::text ORDER BY acn.position) AS artist_mbids
             , jsonb_agg(
                    jsonb_build_object(
                        'artist_credit_name', acn.name,
                        'join_phrase', acn.join_phrase,
                        'artist_mbid', a.gid::TEXT
                    )
                    ORDER BY acn.position
               ) AS artists
          FROM musicbrainz.recording r
          JOIN musicbrainz.artist_credit_name acn
            ON acn.artist_credit = r.artist_credit
          JOIN musicbrainz.artist a
            ON a.id = acn.artist
         {mbid_filter_clause}
      GROUP BY r.gid
    """
