def get_artist_credit_cache_query(with_filter: bool = False):
    """ Import artist credit data from postgres to HDFS.

        If with_filter is True, the query is prepared in a way such that it can be filtered using a list of
        artist mbids passed as a VALUES list.
    """
    cte_clause = ""
    mbid_filter_clause = ""
    if with_filter:
        cte_clause = "WITH mbids (mbid) AS (VALUES %s)"
        mbid_filter_clause = "JOIN mbids m ON m.mbid = a.gid"

    return f"""
        {cte_clause}
        SELECT ac.id AS artist_credit_id
             , a.gid::text AS artist_mbid
             , acn.position
             , acn.join_phrase
          FROM musicbrainz.artist_credit ac
          JOIN musicbrainz.artist_credit_name acn
            ON acn.artist_credit = ac.id
          JOIN musicbrainz.artist a
            ON acn.artist = a.id
        {mbid_filter_clause}
    """
