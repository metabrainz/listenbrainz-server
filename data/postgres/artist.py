def get_artist_country_cache_query(with_filter: bool = False):
    """ Import artist country from postgres to HDFS for use in artist map stats calculation.

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
        SELECT a.gid::text AS artist_mbid
             , a.name AS artist_name
             , iso.code AS country_code_alpha_2
          FROM musicbrainz.artist a
          JOIN musicbrainz.area_containment ac
            ON ac.descendant = a.area
          JOIN musicbrainz.iso_3166_1 iso
            ON iso.area = ac.parent
         {mbid_filter_clause}
         UNION
         -- for the case where artist area is a country itself
        SELECT a.gid::text AS artist_mbid
             , a.name AS artist_name
             , iso.code AS country_code_alpha_2
          FROM musicbrainz.artist a
          JOIN musicbrainz.iso_3166_1 iso
            ON iso.area = a.area
         {mbid_filter_clause}
        -- for the case where artist area is null
         UNION
        SELECT a.gid::text AS artist_mbid
             , a.name AS artist_name
             , NULL AS country_code_alpha_2
          FROM musicbrainz.artist a
         {mbid_filter_clause}
         WHERE a.area IS NULL
    """
