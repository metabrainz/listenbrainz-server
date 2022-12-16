from listenbrainz_spark.path import RELEASE_GROUPS_YEAR_DATAFRAME
from listenbrainz_spark.postgres.utils import save_pg_table_to_hdfs


def create_year_release_groups(year):
    """ Import release groups which were released in the given year from postgres to HDFS """
    query = f"""
        WITH rg_cover_art AS (
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
        )
            SELECT rg.gid AS release_group_mbid
                 , rg.name AS title
                 , ac.name AS artist_credit_name
                 , rgca.caa_id AS caa_id
                 , rgca.caa_release_mbid AS caa_release_mbid
                 , array_agg(a.gid ORDER BY acn.position) AS artist_credit_mbids
              FROM musicbrainz.release_group rg
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
             WHERE rgm.first_release_date_year = {year}
          GROUP BY rg.gid
                 , rg.name
                 , make_date(rgm.first_release_date_year, rgm.first_release_date_month, rgm.first_release_date_day)
                 , ac.name
                 , rgca.caa_id
                 , rgca.caa_release_mbid
    """

    save_pg_table_to_hdfs(query, RELEASE_GROUPS_YEAR_DATAFRAME)
