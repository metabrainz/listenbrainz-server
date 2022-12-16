import listenbrainz_spark
from data.model.new_releases_stat import NewReleasesStat
from listenbrainz_spark import config
from listenbrainz_spark.path import RELEASE_GROUPS_YEAR_DATAFRAME
from listenbrainz_spark.postgres.release_group import create_year_release_groups

from listenbrainz_spark.stats import run_query
from listenbrainz_spark.year_in_music.utils import setup_listens_for_year


def get_new_releases_of_top_artists(year):
    setup_listens_for_year(year)

    create_year_release_groups(year)
    listenbrainz_spark\
        .sql_context\
        .read\
        .parquet(config.HDFS_CLUSTER_URI + RELEASE_GROUPS_YEAR_DATAFRAME)\
        .createOrReplaceTempView("release_groups_of_year")

    run_query(_get_top_50_artists()).createOrReplaceTempView("top_50_artists")
    new_releases = run_query(_get_new_releases_of_top_artists()).toLocalIterator()

    for entry in new_releases:
        data = entry.asDict(recursive=True)
        yield NewReleasesStat(
            type="year_in_music_new_releases_of_top_artists",
            year=year,
            user_id=data["user_id"],
            data=data["new_releases"]
        ).dict(exclude_none=True)


def _get_top_50_artists():
    return """
        WITH intermediate_table as (
            SELECT user_id
                 , artist_credit_mbids
                 , count(*) as listen_count
              FROM listens_of_year
             WHERE artist_credit_mbids IS NOT NULL
          GROUP BY user_id
                 , artist_credit_mbids
        ), intermediate_table_2 AS (
            SELECT user_id
                 , artist_credit_mbids
                 , listen_count
                 , row_number() OVER(PARTITION BY user_id ORDER BY listen_count DESC) AS row_number
              FROM intermediate_table
        )
            SELECT user_id
                 , artist_credit_mbids
                 , listen_count
              FROM intermediate_table_2
             WHERE row_number <= 50
    """

def _get_new_releases_of_top_artists():
    return """
        SELECT user_id
             , collect_list(
                    struct(
                       rgoy.title
                     , rgoy.artist_credit_name  
                     , rgoy.release_group_mbid
                     , rgoy.artist_credit_mbids
                     , rgoy.caa_id
                     , rgoy.caa_release_mbid
                    )
               ) AS new_releases
          FROM release_groups_of_year rgoy
          JOIN top_50_artists t50a
            ON cardinality(array_intersect(rgoy.artist_credit_mbids, t50a.artist_credit_mbids)) > 0
      GROUP BY user_id
    """
