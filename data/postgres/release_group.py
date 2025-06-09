def get_release_group_metadata_cache_query(with_filter: bool = False):
    """ Import release groups with cover art data from postgres to HDFS.

        If with_filter is True, the query is prepared in a way such that it can be filtered using a list of
        release group mbids passed as a VALUES list.
    """
    cte_clause = ""
    mbid_filter_clause = ""
    if with_filter:
        cte_clause = "mbids (mbid) AS (VALUES %s), "
        mbid_filter_clause = "JOIN mbids m ON m.mbid = rg.gid"

    return f"""
        WITH {cte_clause} rg_cover_art AS (
            SELECT DISTINCT ON (rg.id)
                   rg.id AS release_group
                 , caa.id AS caa_id
                 , caa_rel.gid AS caa_release_mbid
              FROM musicbrainz.release_group rg
              {mbid_filter_clause}
              JOIN musicbrainz.release caa_rel
                ON rg.id = caa_rel.release_group
         LEFT JOIN (
                  SELECT release, date_year, date_month, date_day
                    FROM musicbrainz.release_country
               UNION ALL
                  SELECT release, date_year, date_month, date_day
                    FROM musicbrainz.release_unknown_country
                 ) re
                ON (re.release = caa_rel.id)
         FULL JOIN cover_art_archive.release_group_cover_art rgca
                ON rgca.release = caa_rel.id
         LEFT JOIN cover_art_archive.cover_art caa
                ON caa.release = caa_rel.id
         LEFT JOIN cover_art_archive.cover_art_type cat
                ON cat.id = caa.id
             WHERE type_id = 1
               AND mime_type != 'application/pdf'
          ORDER BY rg.id
                 , rgca.release
                 , re.date_year
                 , re.date_month
                 , re.date_day
                 , caa.ordering
        )
            SELECT rg.gid::text AS release_group_mbid
                 , rg.name AS title
                 , ac.name AS artist_credit_name
                 , rgca.caa_id AS caa_id
                 , rgca.caa_release_mbid::text AS caa_release_mbid
                 , array_agg(a.gid::text ORDER BY acn.position) AS artist_credit_mbids
                 , jsonb_agg(
                        jsonb_build_object(
                            'artist_credit_name', acn.name,
                            'join_phrase', acn.join_phrase,
                            'artist_mbid', a.gid::TEXT
                        )
                        ORDER BY acn.position
                    ) AS artists
                 , rgm.first_release_date_year
              FROM musicbrainz.release_group rg
              {mbid_filter_clause}
              JOIN musicbrainz.release_group_meta rgm
                ON rgm.id = rg.id
              JOIN musicbrainz.artist_credit ac
                ON rg.artist_credit = ac.id
              JOIN musicbrainz.artist_credit_name acn
                ON ac.id = acn.artist_credit
              JOIN musicbrainz.artist a
                ON acn.artist = a.id
         LEFT JOIN rg_cover_art rgca
                ON rgca.release_group = rg.id
          GROUP BY rg.gid
                 , rg.name
                 , rgm.first_release_date_year
                 , make_date(rgm.first_release_date_year, rgm.first_release_date_month, rgm.first_release_date_day)
                 , ac.name
                 , rgca.caa_id
                 , rgca.caa_release_mbid
    """
