from typing import Optional

from pyspark import StorageLevel
from pyspark.sql import DataFrame

from listenbrainz_spark.path import RELEASE_METADATA_CACHE_DATAFRAME
from listenbrainz_spark.postgres.utils import save_pg_table_to_hdfs
from listenbrainz_spark.utils import read_files_from_HDFS

_RELEASE_METADATA_CACHE = "release_metadata_cache"
_release_metadata_df: Optional[DataFrame] = None


def create_release_metadata_cache():
    """ Import release metadata from postgres to HDFS for use in stats calculation. """
    query = """
          WITH release_group_cover_art AS (
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
                SELECT release_mbid
                     , release_group_mbid
                     , first_release_date_year
                     , release_name
                     , album_artist_name
                     , caa_id
                     , caa_release_mbid
                     , array_agg(artist_mbid ORDER BY position) AS artist_credit_mbids
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

    save_pg_table_to_hdfs(query, RELEASE_METADATA_CACHE_DATAFRAME, process_artists_column=True)

    unpersist_release_metadata_cache()


def get_release_metadata_cache():
    """ Read the RELEASE_METADATA_CACHE parquet files from HDFS and create a spark SQL view
     if one already doesn't exist """
    global _release_metadata_df
    if _release_metadata_df is None:
        _release_metadata_df = read_files_from_HDFS(RELEASE_METADATA_CACHE_DATAFRAME)
        _release_metadata_df.persist(StorageLevel.DISK_ONLY)
        _release_metadata_df.createOrReplaceTempView(_RELEASE_METADATA_CACHE)
    return _RELEASE_METADATA_CACHE


def unpersist_release_metadata_cache():
    global _release_metadata_df
    if _release_metadata_df is not None:
        _release_metadata_df.unpersist()
        _release_metadata_df = None
