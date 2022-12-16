from datetime import datetime, date, time

import listenbrainz_spark
from data.model.new_releases_stat import NewReleasesStat
from listenbrainz_spark import config
from listenbrainz_spark.path import RELEASE_GROUPS_YEAR_DATAFRAME
from listenbrainz_spark.postgres.release_group import create_year_release_groups

from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import get_all_listens_from_new_dump
from listenbrainz_spark.year_in_music.utils import setup_listens_for_year


def get_new_releases_of_top_artists(year):
    get_all_listens_from_new_dump().createOrReplaceTempView("listens")
    create_year_release_groups(year)
    listenbrainz_spark\
        .sql_context\
        .read\
        .parquet(config.HDFS_CLUSTER_URI + RELEASE_GROUPS_YEAR_DATAFRAME)\
        .createOrReplaceTempView("release_groups_of_year")

    new_releases = run_query(_get_new_releases_of_top_artists(year))

    for entry in new_releases.toLocalIterator():
        data = entry.asDict(recursive=True)
        yield NewReleasesStat(
            type="year_in_music_new_releases_of_top_artists",
            year=year,
            user_id=data["user_id"],
            data=data["new_releases"]
        ).dict(exclude_none=True)


def _get_new_releases_of_top_artists(year):
    start = datetime.combine(date(year, 1, 1), time.min)
    end = datetime.combine(date(year, 12, 31), time.max)
    return f"""
        WITH artist_counts as (
            SELECT user_id
                 , artist_credit_mbids
                 , count(*) as listen_count
              FROM listens
             WHERE listened_at >= to_timestamp('{start}')
               AND listened_at <= to_timestamp('{end}')
               AND artist_credit_mbids IS NOT NULL
          GROUP BY user_id
                 , artist_credit_mbids
        ), top_artists AS (
            SELECT user_id
                 , artist_credit_mbids
                 , row_number() OVER(PARTITION BY user_id ORDER BY listen_count DESC) AS row_number
              FROM artist_counts
        )
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
              JOIN top_artists t50a
                ON cardinality(array_intersect(rgoy.artist_credit_mbids, t50a.artist_credit_mbids)) > 0
             WHERE row_number <= 50
          GROUP BY user_id
    """
