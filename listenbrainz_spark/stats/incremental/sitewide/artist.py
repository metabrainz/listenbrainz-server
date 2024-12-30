from typing import List

from pyspark.sql.types import StructType, StructField, StringType, IntegerType

import listenbrainz_spark
from listenbrainz_spark import hdfs_connection
from listenbrainz_spark.path import LISTENBRAINZ_INTERMEDIATE_STATS_DIRECTORY, INCREMENTAL_DUMPS_SAVE_PATH
from listenbrainz_spark.stats import run_query, SITEWIDE_STATS_ENTITY_LIMIT
from listenbrainz_spark.utils import read_files_from_HDFS

PATH = "/sitewide_artists_all_time"
schema = StructType([
    StructField('artist_name', StringType(), nullable=False),
    StructField('artist_mbid', StringType(), nullable=True),
    StructField('listen_count', IntegerType(), nullable=False),
])


def aggregate_artists(table: str, cache_tables: List[str]):
    cache_table = cache_tables[0]
    result = run_query(f"""
        WITH exploded_listens AS (
            SELECT user_id
                 , artist_name AS artist_credit_name
                 , explode_outer(artist_credit_mbids) AS artist_mbid
             FROM {table}
        ), listens_with_mb_data as (
            SELECT user_id
                 , COALESCE(at.artist_name, el.artist_credit_name) AS artist_name
                 , el.artist_mbid
              FROM exploded_listens el
         LEFT JOIN {cache_table} at
                ON el.artist_mbid = at.artist_mbid
        )
            SELECT first(any_artist_name) AS artist_name
                 , artist_mbid
                 , count(*) as listen_count
              FROM listens_with_mb_data
          GROUP BY lower(any_artist_name)
                 , artist_mbid
    """)
    return result


def combine_artists(full_table, inc_table):
    query = f"""
        WITH intermediate_table AS (
            SELECT artist_name
                 , artist_mbid
                 , listen_count
              FROM {full_table}
             UNION ALL
            SELECT artist_name
                 , artist_mbid
                 , listen_count
              FROM {inc_table}     
        )
            SELECT first(artist_name) AS artist_name
                 , artist_mbid
                 , sum(listen_count) as total_listen_count
              FROM intermediate_table
          GROUP BY lower(artist_name)
                 , artist_mbid
    """
    return run_query(query)


def top_n_artists(table, N):
    query = f"""
        WITH entity_count AS (
            SELECT count(*) AS total_count
              FROM {table}
        ), ordered_stats AS (
            SELECT *
              FROM {table}
          ORDER BY total_listen_count DESC
             LIMIT {N}
        ), grouped_stats AS (
            SELECT sort_array(
                        collect_list(
                            struct(
                                total_listen_count AS listen_count
                              , artist_name
                              , artist_mbid
                            )
                        )
                        , false
                   ) AS stats
              FROM ordered_stats
        )
            SELECT total_count
                 , stats
              FROM grouped_stats 
              JOIN entity_count
                ON TRUE
    """
    return run_query(query)


def get_artists_incremental(table: str, cache_tables: List[str], user_listen_count_limit, top_artists_limit: int = SITEWIDE_STATS_ENTITY_LIMIT):
    """ Get artist information (artist_name etc) for every time range specified
        the "time_range" table ordered by listen count

        Args:
            table: name of the temporary table
            user_listen_count_limit: per user per entity listen count above which it should be capped
            top_artists_limit: number of top artists to retain
        Returns:
            iterator (iter): An iterator over result
    """
    if not hdfs_connection.client.status(PATH, strict=False):
        read_files_from_HDFS(LISTENBRAINZ_INTERMEDIATE_STATS_DIRECTORY) \
            .createOrReplaceTempView("all_listens_temp_sitewide")
        full_df = aggregate_artists(table, cache_tables)
        full_df.write.mode("overwrite").parquet(PATH)
        full_df = read_files_from_HDFS(PATH)
    else:
        full_df = listenbrainz_spark.session.createDataFrame([], schema=schema)

    if hdfs_connection.client.status(INCREMENTAL_DUMPS_SAVE_PATH, strict=False):
        read_files_from_HDFS(INCREMENTAL_DUMPS_SAVE_PATH) \
            .createOrReplaceTempView("incremental_listens_temp_sitewide")
        inc_df = aggregate_artists(table, cache_tables)
    else:
        inc_df = listenbrainz_spark.session.createDataFrame([], schema=schema)

    full_table = "sitewide_artists_all_time_partial"
    full_df.createOrReplaceTempView(full_table)

    inc_table = "sitewide_artists_all_time_incremental"
    inc_df.createOrReplaceTempView(inc_table)

    combined_table = combine_artists(full_table, inc_table)
    results_df = top_n_artists(combined_table, top_artists_limit)

    return results_df.toLocalIterator()
