from datetime import datetime, date, time

import pycountry
from more_itertools import chunked
from pyspark.sql.types import StructField, StringType

import listenbrainz_spark
from listenbrainz_spark import config
from listenbrainz_spark.path import ARTIST_COUNTRY_CODE_DATAFRAME
from listenbrainz_spark.postgres.artist import create_artist_country_cache
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import get_listens_from_dump


USERS_PER_MESSAGE = 100


def get_artist_map_stats(year):
    start = datetime.combine(date(year, 1, 1), time.min)
    end = datetime.combine(date(year, 12, 31), time.max)
    get_listens_from_dump(start, end).createOrReplaceTempView("listens")

    create_artist_country_cache()

    listenbrainz_spark\
        .sql_context\
        .read\
        .parquet(config.HDFS_CLUSTER_URI + ARTIST_COUNTRY_CODE_DATAFRAME)\
        .createOrReplaceTempView("artist_metadata_cache")

    create_iso_country_codes_df()

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
                 , ic.alpha_3 AS country
                 , artist_mbid
                 , listen_count
              FROM artist_counts ac
              JOIN artist_metadata_cache amc
             USING (artist_mbid)
              JOIN iso_codes ic
                ON ic.alpha_2 = amc.country_code
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


def create_iso_country_codes_df():
    """ Create a dataframe mapping 2 letter iso codes to 3 letter iso country codes because
    MB stores the 2 letter iso code but the frontend needs the 3 letter iso code."""
    iso_codes = []
    for country in pycountry.countries:
        iso_codes.append((country.alpha_2, country.alpha_3))

    df = listenbrainz_spark.session.createDataFrame(iso_codes, schema=["alpha_2", "alpha_3"])
    df.createOrReplaceTempView("iso_codes")
