def get_artist_country_cache_query(with_filter: bool = False):
    """ Import artist country from postgres to HDFS for use in artist map stats calculation.

        If with_filter is True, the query is prepared in a way such that it can be filtered using a list of
        artist mbids passed as a VALUES list.

        The query uses DISTINCT ON to deduplicate artists, preferring (in order):
        1. Artist area is a country or independent territory itself (direct iso_3166_1 match)
        2. Artist area is contained in a country (via area_containment)
        3. Artist area is null
    """
    cte_clause = ""
    mbid_filter_clause = ""
    if with_filter:
        cte_clause = "WITH mbids (mbid) AS (VALUES %s)"
        mbid_filter_clause = "JOIN mbids m ON m.mbid = a.gid"

    return f"""
        {cte_clause}
        SELECT DISTINCT ON (artist_mbid, artist_name)
               artist_mbid
             , artist_name
             , country_code_alpha_2
          FROM (
            -- for the case where artist area has a top level iso-3166-1 code (usually countries)
        SELECT a.gid::text AS artist_mbid
             , a.name AS artist_name
             , iso.code AS country_code_alpha_2
             , 1 AS priority
          FROM musicbrainz.artist a
          JOIN musicbrainz.iso_3166_1 iso
            ON iso.area = a.area
         {mbid_filter_clause}
         UNION
          -- for the case where artist area is a subdivision of a country
        SELECT a.gid::text AS artist_mbid
             , a.name AS artist_name
             , iso.code AS country_code_alpha_2
             , 2 AS priority
          FROM musicbrainz.artist a
          JOIN musicbrainz.area_containment ac
            ON ac.descendant = a.area
          JOIN musicbrainz.iso_3166_1 iso
            ON iso.area = ac.parent
         {mbid_filter_clause}
        -- for the case where artist area is null
         UNION
        SELECT a.gid::text AS artist_mbid
             , a.name AS artist_name
             , NULL AS country_code_alpha_2
             , 3 AS priority
          FROM musicbrainz.artist a
         {mbid_filter_clause}
         WHERE a.area IS NULL
             ) t
      ORDER BY artist_mbid, artist_name, priority
    """
