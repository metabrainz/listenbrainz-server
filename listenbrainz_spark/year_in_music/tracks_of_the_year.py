from datetime import datetime, date, time

from listenbrainz_spark import config
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import get_all_listens_from_new_dump


def calculate_tracks_of_the_year(year):
    """ Calculate all tracks a user has listened to in the given year. """
    get_all_listens_from_new_dump().createOrReplaceTempView("listens")

    start = datetime.combine(date(year, 1, 1), time.min)
    end = datetime.combine(date(year, 12, 31), time.max)

    query = f"""
        SELECT user_id
             , recording_name
             , recording_mbid
             , artist_name
             , artist_credit_mbids
             , count(*) AS listen_count
          FROM listens
         WHERE listened_at >= to_timestamp('{start}')
           AND listened_at <= to_timestamp('{end}')
           AND recording_mbid IS NOT NULL
      GROUP BY user_id
             , recording_name
             , recording_mbid
             , artist_name
             , artist_credit_mbids
    """

    run_query(query).write.format("json").save(config.HDFS_CLUSTER_URI + "/tracks_of_the_year", mode="overwrite")
