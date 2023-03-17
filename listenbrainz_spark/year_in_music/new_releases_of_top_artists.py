from datetime import datetime, date, time

import listenbrainz_spark
from data.model.new_releases_stat import NewReleasesStat
from listenbrainz_spark import config
from listenbrainz_spark.path import RELEASE_GROUPS_YEAR_DATAFRAME
from listenbrainz_spark.postgres.release_group import create_year_release_groups

from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import get_listens_from_dump


def get_new_releases_of_top_artists(year):
    from_date = datetime(year, 1, 1)
    to_date = datetime.combine(date(year, 12, 31), time.max)
    get_listens_from_dump(from_date, to_date).createOrReplaceTempView("listens")

    create_year_release_groups(year)
    listenbrainz_spark\
        .sql_context\
        .read\
        .parquet(config.HDFS_CLUSTER_URI + RELEASE_GROUPS_YEAR_DATAFRAME)\
        .createOrReplaceTempView("release_groups_of_year")

    new_releases = run_query(_get_new_releases_of_top_artists())

    for entry in new_releases.toLocalIterator():
        data = entry.asDict(recursive=True)
        yield NewReleasesStat(
            type="year_in_music_new_releases_of_top_artists",
            year=year,
            user_id=data["user_id"],
            data=data["new_releases"]
        ).dict(exclude_none=True)


def _get_new_releases_of_top_artists():
    # instead of exploding the artist mbids, it is possible to use arrays_overlap on the two artist credit mbids
    # however in that case spark will do a BroadcastNestedLoopJoin which is very slow (takes 3 hours). the query
    # below using equality on artist mbid takes 2 minutes.
    return f"""
        WITH artist_counts as (
            SELECT user_id
                 , artist_credit_mbids
                 , count(*) as listen_count
              FROM listens
             WHERE artist_credit_mbids IS NOT NULL
          GROUP BY user_id
                 , artist_credit_mbids
        ), top_artists AS (
            SELECT user_id
                 , artist_credit_mbids
                 , row_number() OVER(PARTITION BY user_id ORDER BY listen_count DESC) AS row_number
              FROM artist_counts
        ), top_50_artists AS (
            SELECT user_id
                 , explode(artist_credit_mbids) AS artist_mbid
              FROM top_artists
             WHERE row_number <= 50   
        ), release_groups AS (
            SELECT title
                 , artist_credit_name  
                 , release_group_mbid
                 , artist_credit_mbids
                 , caa_id
                 , caa_release_mbid
                 , explode(artist_credit_mbids) AS artist_mbid
              FROM release_groups_of_year    
        )
            SELECT user_id
                 , collect_set(
                        struct(
                           rg.title
                         , rg.artist_credit_name  
                         , rg.release_group_mbid
                         , rg.artist_credit_mbids
                         , rg.caa_id
                         , rg.caa_release_mbid
                        )
                    ) AS new_releases
              FROM release_groups rg
              JOIN top_50_artists t50a
             WHERE rg.artist_mbid = t50a.artist_mbid
          GROUP BY user_id
    """
