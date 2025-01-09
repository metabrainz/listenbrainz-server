from typing import List

from pyspark.sql.types import StructType, StructField, StringType, IntegerType, ArrayType

from listenbrainz_spark.path import RELEASE_METADATA_CACHE_DATAFRAME, \
    RELEASE_GROUP_METADATA_CACHE_DATAFRAME
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.stats.incremental.listener.entity import EntityListener


class ReleaseGroupEntityListener(EntityListener):

    def __init__(self, stats_range, database):
        super().__init__(
            entity="release_groups", stats_range=stats_range,
            database=database, message_type="entity_listener"
        )

    def get_cache_tables(self) -> List[str]:
        return [RELEASE_METADATA_CACHE_DATAFRAME, RELEASE_GROUP_METADATA_CACHE_DATAFRAME]

    def get_partial_aggregate_schema(self):
        return StructType([
            StructField("release_group_mbid", StringType(), nullable=False),
            StructField("release_group_name", StringType(), nullable=False),
            StructField("release_group_artist_name", StringType(), nullable=False),
            StructField("artist_credit_mbids", ArrayType(StringType()), nullable=False),
            StructField("caa_id", IntegerType(), nullable=True),
            StructField("caa_release_mbid", StringType(), nullable=True),
            StructField("user_id", IntegerType(), nullable=False),
            StructField("listen_count", IntegerType(), nullable=False),
        ])

    def get_entity_id(self):
        return "release_group_mbid"

    def aggregate(self, table, cache_tables):
        rel_cache_table = cache_tables[0]
        rg_cache_table = cache_tables[1]
        result = run_query(f"""
            WITH gather_release_data AS (
                SELECT user_id
                     , rg.release_group_mbid
                     -- this is intentional as we don't have a release group name field in listen submission json
                     -- and for the purposes of this stat, they'd usually be the same.
                     , COALESCE(rg.title, l.release_name) AS release_group_name
                     , COALESCE(rg.artist_credit_name, l.artist_name) AS release_group_artist_name
                     , COALESCE(rg.artist_credit_mbids, l.artist_credit_mbids) AS artist_credit_mbids
                     , rg.caa_id
                     , rg.caa_release_mbid
                  FROM {table} l
             LEFT JOIN {rel_cache_table} rel
                    ON rel.release_mbid = l.release_mbid
             LEFT JOIN {rg_cache_table} rg
                    ON rg.release_group_mbid = rel.release_group_mbid
            )
                SELECT release_group_mbid
                     , release_group_name
                     , release_group_artist_name
                     , artist_credit_mbids
                     , caa_id
                     , caa_release_mbid
                     , user_id
                     , count(*) AS listen_count
                  FROM gather_release_data
              GROUP BY release_group_mbid
                     , release_group_name
                     , release_group_artist_name
                     , artist_credit_mbids
                     , caa_id
                     , caa_release_mbid
                     , user_id
        """)
        return result

    def combine_aggregates(self, existing_aggregate, incremental_aggregate):
        query = f"""
            WITH intermediate_table AS (
                SELECT release_group_mbid
                     , release_group_name
                     , release_group_artist_name
                     , artist_credit_mbids
                     , caa_id
                     , caa_release_mbid
                     , user_id
                     , listen_count
                  FROM {existing_aggregate}
                 UNION ALL
                SELECT release_group_mbid
                     , release_group_name
                     , release_group_artist_name
                     , artist_credit_mbids
                     , caa_id
                     , caa_release_mbid
                     , user_id
                     , listen_count
                  FROM {incremental_aggregate}     
            )
                SELECT release_group_mbid
                     , release_group_name
                     , release_group_artist_name
                     , artist_credit_mbids
                     , caa_id
                     , caa_release_mbid
                     , user_id
                     , sum(listen_count) as listen_count
                  FROM intermediate_table
              GROUP BY release_group_mbid
                     , release_group_name
                     , release_group_artist_name
                     , artist_credit_mbids
                     , caa_id
                     , caa_release_mbid
                     , user_id
        """
        return run_query(query)

    def get_top_n(self, final_aggregate, N):
        query = f"""
            WITH entity_count as (
            SELECT release_group_mbid
                 , SUM(listen_count) as total_listen_count
                 , COUNT(DISTINCT user_id) as total_user_count
              FROM {final_aggregate}
          GROUP BY release_group_mbid
        ), ranked_stats as (
            SELECT release_group_mbid
                 , release_group_name
                 , release_group_artist_name AS artist_name
                 , artist_credit_mbids AS artist_mbids
                 , caa_id
                 , caa_release_mbid
                 , user_id 
                 , listen_count
                 , row_number() OVER (PARTITION BY release_group_mbid ORDER BY listen_count DESC) AS rank
              FROM {final_aggregate}
        ), grouped_stats AS (
            SELECT release_group_mbid
                 , release_group_name
                 , artist_name
                 , artist_mbids
                 , caa_id
                 , caa_release_mbid
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
          GROUP BY release_group_mbid
                 , release_group_name
                 , artist_name
                 , artist_mbids
                 , caa_id
                 , caa_release_mbid
        )
            SELECT release_group_mbid
                 , release_group_name
                 , artist_name
                 , artist_mbids
                 , caa_id
                 , caa_release_mbid
                 , listeners
                 , total_listen_count
                 , total_user_count
              FROM grouped_stats
              JOIN entity_count
             USING (release_group_mbid)
        """
        return run_query(query)
