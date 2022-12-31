from datetime import datetime, date, time

from more_itertools import chunked

import listenbrainz_spark
from listenbrainz_spark import config
from listenbrainz_spark.path import ARTIST_COUNTRY_CODE_DATAFRAME
from listenbrainz_spark.postgres.artist import create_artist_country_cache
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import get_all_listens_from_new_dump


USERS_PER_MESSAGE = 100


def get_artist_map_stats(year):
    get_all_listens_from_new_dump().createOrReplaceTempView("listens")
    create_artist_country_cache()

    listenbrainz_spark\
        .sql_context\
        .read\
        .parquet(config.HDFS_CLUSTER_URI + ARTIST_COUNTRY_CODE_DATAFRAME)\
        .createOrReplaceTempView("artist_metadata_cache")

    start = datetime.combine(date(year, 1, 1), time.min)
    end = datetime.combine(date(year, 12, 31), time.max)

    query = f"""
          WITH exploded_listens as (
            SELECT user_id
                 , explode(artist_credit_mbids) AS artist_mbid
              FROM listens
             WHERE listened_at >= to_timestamp('{start}')
               AND listened_at <= to_timestamp('{end}')
               AND artist_credit_mbids IS NOT NULL
          ), artist_counts AS (
            SELECT user_id
                 , artist_mbid
                 , count(artist_mbid) AS listen_count
              FROM exploded_listens
          GROUP BY user_id
                 , artist_mbid  
          ), artist_data AS (
            SELECT user_id
                 , artist_name
                 , country_code AS country
                 , artist_mbid
                 , listen_count
              FROM artist_counts ac
              JOIN artist_metadata_cache amc
             USING (artist_mbid)
          ), user_country_data AS (
            SELECT user_id
                 , country
                 , COUNT(artist_mbid) AS artist_count
                 , SUM(listen_count) AS listen_count
                 , sort_array(
                        collect_list(struct(listen_count, artist_name, artist_mbid))
                      , false
                   ) as artists
              FROM artist_data
          GROUP BY user_id
                 , country
          ) SELECT user_id
                 , sort_array(
                        collect_list(struct(listen_count, country, artist_count, artists))
                        , false
                   ) as data
              FROM user_country_data
          GROUP BY user_id       
    """

    data = run_query(query)
    for entry in chunked(data.toLocalIterator(), USERS_PER_MESSAGE):
        yield {
            "type": "year_in_music_artist_map",
            "year": year,
            "data": [row.asDict(recursive=True) for row in entry],
        }
