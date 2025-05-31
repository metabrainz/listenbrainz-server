def get_tag_or_genre_cache_query(entity, *, only_genres, with_filter):
    """ Import tag or genre data from musicbrainz from postgres to HDFS for use in artist map stats calculation.

        If with_filter is True, the query is prepared in a way such that it can be filtered using a list of
        entity mbids passed as a VALUES list.
    """
    if entity not in {"recording", "artist", "release_group"}:
        raise ValueError(f"{entity} not a valid entity")

    if only_genres:
        genre_join = """
            JOIN musicbrainz.genre g
              ON t.name = g.name
        """
        name_alias = "genre"
    else:
        genre_join = ""
        name_alias = "tag"

    cte_clause = ""
    mbid_filter_clause = ""
    if with_filter:
        if entity == "recording" or entity == "artist":
            cte_clause = "WITH mbids (mbid) AS (VALUES %s)"
        else:
            cte_clause = "mbids (mbid) AS (VALUES %s), "
        mbid_filter_clause = "JOIN mbids m ON m.mbid = e.gid"

    if entity == "recording":
        return f"""
            {cte_clause}
            SELECT e.gid::text AS recording_mbid
                 , t.name AS {name_alias}
                 , count AS {name_alias}_count
              FROM musicbrainz.tag t
                {genre_join}
              JOIN musicbrainz.recording_tag rt
                ON rt.tag = t.id
              JOIN musicbrainz.recording e
                ON rt.recording = e.id
                {mbid_filter_clause}
             WHERE count > 0
        """
    elif entity == "artist":
        return f"""
            {cte_clause}
        SELECT e.gid::text AS recording_mbid
             , t.name AS {name_alias}
             , SUM(count) AS {name_alias}_count
          FROM musicbrainz.recording e
            {mbid_filter_clause}
          JOIN musicbrainz.artist_credit_name acn
            ON e.artist_credit = acn.artist_credit
          JOIN musicbrainz.artist a
            ON acn.artist = a.id
          JOIN musicbrainz.artist_tag at
            ON at.artist = a.id
          JOIN musicbrainz.tag t
            ON at.tag = t.id
            {genre_join}
         WHERE count > 0
      GROUP BY e.gid
             , t.name
    """
    else:
        return f"""
    WITH {cte_clause} intermediate AS (
        SELECT e.gid AS recording_mbid
             , t.name AS {name_alias}
             , SUM(count) AS {name_alias}_count
          FROM musicbrainz.release_group_tag rgt
          JOIN musicbrainz.tag t
            ON rgt.tag = t.id
            {genre_join}
          JOIN musicbrainz.release_group rg
            ON rgt.release_group = rg.id
          JOIN musicbrainz.release rel
            ON rel.release_group = rg.id
          JOIN musicbrainz.medium med
            ON med.release = rel.id
          JOIN musicbrainz.track tr
            ON tr.medium = med.id
          JOIN musicbrainz.recording e
            ON tr.recording = e.id
            {mbid_filter_clause}
         WHERE count > 0
      GROUP BY e.gid
             , t.name
         UNION ALL
        SELECT e.gid AS recording_mbid
             , t.name AS {name_alias}
             , SUM(count) AS {name_alias}_count
          FROM musicbrainz.release_tag rlt
          JOIN musicbrainz.tag t
            ON rlt.tag = t.id
            {genre_join}
          JOIN musicbrainz.release rl
            ON rlt.release = rl.id  
          JOIN musicbrainz.release_group rg
            ON rl.release_group = rg.id
          JOIN musicbrainz.release rel
            ON rel.release_group = rg.id
          JOIN musicbrainz.medium med
            ON med.release = rel.id
          JOIN musicbrainz.track tr
            ON tr.medium = med.id
          JOIN musicbrainz.recording e
            ON tr.recording = e.id
            {mbid_filter_clause}
         WHERE count > 0
      GROUP BY e.gid
             , t.name
    ) SELECT recording_mbid::text
           , {name_alias}
           , CAST(SUM({name_alias}_count) AS BIGINT) AS {name_alias}_count
        FROM intermediate
    GROUP BY recording_mbid
           , {name_alias}
    """
