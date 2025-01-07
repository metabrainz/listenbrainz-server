from typing import List

from pyspark.sql.types import StructType, StructField, StringType, IntegerType

from listenbrainz_spark.path import ARTIST_COUNTRY_CODE_DATAFRAME
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.stats.incremental.listener.entity import EntityListener
from listenbrainz_spark.stats.incremental.user.entity import UserEntity


class ArtistEntityListener(EntityListener):

    def __init__(self):
        super().__init__(entity="artists")

    def get_cache_tables(self) -> List[str]:
        return [ARTIST_COUNTRY_CODE_DATAFRAME]

    def get_partial_aggregate_schema(self):
        return StructType([
            StructField('artist_name', StringType(), nullable=False),
            StructField('artist_mbid', StringType(), nullable=True),
            StructField('user_id', IntegerType(), nullable=False),
            StructField('listen_count', IntegerType(), nullable=False),
        ])

    def filter_existing_aggregate(self, existing_aggregate, incremental_aggregate):
        query = f"""
            WITH incremental_artists AS (
                SELECT DISTINCT artist_mbid FROM {incremental_aggregate}
            )
            SELECT *
              FROM {existing_aggregate} ea
             WHERE EXISTS(SELECT 1 FROM incremental_artists iu WHERE iu.artist_mbid = ea.artist_mbid)
        """
        return run_query(query)

    def aggregate(self, table, cache_tables):
        cache_table = cache_tables[0]
        result = run_query(f"""
            WITH exploded_listens AS (
                SELECT user_id
                     , explode_outer(artist_credit_mbids) AS artist_mbid
                  FROM {table}
            ), listens_with_mb_data as (
                SELECT user_id
                     , artist_mbid
                     , at.artist_name
                  FROM exploded_listens el
                  JOIN {cache_table} at
                 USING (artist_mbid)
            )
                SELECT artist_mbid
                     , artist_name
                     , user_id
                     , count(*) AS listen_count
                  FROM listens_with_mb_data
              GROUP BY artist_mbid
                     , artist_name
                     , user_id
        """)
        return result

    def combine_aggregates(self, existing_aggregate, incremental_aggregate):
        query = f"""
            WITH intermediate_table AS (
                SELECT user_id
                     , artist_name
                     , artist_mbid
                     , listen_count
                  FROM {existing_aggregate}
                 UNION ALL
                SELECT user_id
                     , artist_name
                     , artist_mbid
                     , listen_count
                  FROM {incremental_aggregate}     
            )
                SELECT artist_mbid
                     , artist_name
                     , user_id
                     , sum(listen_count) as listen_count
                  FROM intermediate_table
              GROUP BY artist_mbid
                     , artist_name
                     , user_id
        """
        return run_query(query)

    def get_top_n(self, final_aggregate, N):
        query = f"""
            WITH entity_count as (
                SELECT artist_mbid
                     , SUM(listen_count) as total_listen_count
                     , COUNT(DISTINCT user_id) as total_user_count
                  FROM {final_aggregate}
              GROUP BY artist_mbid      
            ), ranked_stats as (
                SELECT artist_mbid
                     , artist_name
                     , user_id 
                     , listen_count
                     , row_number() OVER (PARTITION BY artist_mbid ORDER BY listen_count DESC) AS rank
                  FROM {final_aggregate}
            ), grouped_stats AS (
                SELECT artist_mbid
                     , artist_name
                     , sort_array(
                            collect_list(
                                struct(
                                    listen_count
                                  , user_id 
                                )
                            )
                            , false
                       ) as listeners
                  FROM ranked_stats
                 WHERE rank < {N}
              GROUP BY artist_mbid
                     , artist_name
            )
                SELECT artist_mbid
                     , artist_name
                     , listeners
                     , total_listen_count
                     , total_user_count
                  FROM grouped_stats
                  JOIN entity_count
                 USING (artist_mbid)
        """
        return run_query(query)
