def get_release_metadata_cache_query(with_filter: bool = False):
    """ Import release metadata from postgres to HDFS for use in stats calculation.

        If with_filter is True, the query is prepared in a way such that it can be filtered using a list of
        release group mbids passed as a VALUES list.
    """
    cte_clause = ""
    mbid_filter_clause = ""
    if with_filter:
        cte_clause = "mbids (mbid) AS (VALUES %s), "
        mbid_filter_clause = "JOIN mbids m ON m.mbid = rel.gid"

    return f"""
          WITH {cte_clause} release_group_cover_art AS (
                SELECT DISTINCT ON (rg.id)
                       rg.id AS release_group
                     , caa.id AS caa_id
                     , caa_rel.gid AS caa_release_mbid
                  FROM musicbrainz.release_group rg
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
          ), release_cover_art AS (
                SELECT DISTINCT ON (rel.gid)
                       rel.gid AS release_mbid
                     , caa.id AS caa_id
                     , rel.gid AS caa_release_mbid
                  FROM musicbrainz.release rel
                    {mbid_filter_clause}
                  JOIN cover_art_archive.cover_art caa
                    ON caa.release = rel.id
                  JOIN cover_art_archive.cover_art_type cat
                    ON cat.id = caa.id
                 WHERE type_id = 1
                   AND mime_type != 'application/pdf'
              ORDER BY rel.gid
                     , caa.ordering
          ), intermediate AS (
                SELECT rel.gid AS release_mbid
                     , rg.gid AS release_group_mbid
                     , rgm.first_release_date_year
                     , rel.name AS release_name
                     , ac.name AS album_artist_name
                     , COALESCE(rac.caa_id, rgac.caa_id) AS caa_id
                     , COALESCE(rac.caa_release_mbid, rgac.caa_release_mbid) AS caa_release_mbid
                     , a.gid AS artist_mbid
                     , acn.name AS ac_name
                     , acn.join_phrase AS ac_joinphrase
                     , acn.position
                  FROM musicbrainz.release rel
                    {mbid_filter_clause}
                  JOIN musicbrainz.release_group rg
                    ON rel.release_group = rg.id
                  JOIN musicbrainz.artist_credit ac
                    ON rel.artist_credit = ac.id
                  JOIN musicbrainz.artist_credit_name acn
                    ON acn.artist_credit = ac.id
                  JOIN musicbrainz.artist a
                    ON acn.artist = a.id
             LEFT JOIN musicbrainz.release_group_meta rgm
                    ON rg.id = rgm.id
             LEFT JOIN release_cover_art rac
                    ON rac.release_mbid = rel.gid
             LEFT JOIN release_group_cover_art rgac
                    ON rgac.release_group = rel.release_group
          )
                SELECT release_mbid::text
                     , release_group_mbid::text
                     , first_release_date_year
                     , release_name
                     , album_artist_name
                     , caa_id
                     , caa_release_mbid::text
                     , array_agg(artist_mbid::text ORDER BY position) AS artist_credit_mbids
                     , jsonb_agg(
                        jsonb_build_object(
                            'artist_credit_name', ac_name,
                            'join_phrase', ac_joinphrase,
                            'artist_mbid', artist_mbid
                        )
                        ORDER BY position
                       ) AS artists
                  FROM intermediate
              GROUP BY release_mbid
                     , release_group_mbid
                     , first_release_date_year
                     , release_name
                     , album_artist_name
                     , caa_id
                     , caa_release_mbid
    """
