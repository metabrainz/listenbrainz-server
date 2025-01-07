from typing import List

from pyspark.sql.types import StructType, StructField, StringType, IntegerType, ArrayType

from listenbrainz_spark.path import RELEASE_METADATA_CACHE_DATAFRAME, RELEASE_GROUP_METADATA_CACHE_DATAFRAME
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.stats.incremental.sitewide.entity import SitewideEntity


class ReleaseGroupSitewideEntity(SitewideEntity):

    def __init__(self):
        super().__init__(entity="release_groups")

    def get_cache_tables(self) -> List[str]:
        return [RELEASE_METADATA_CACHE_DATAFRAME, RELEASE_GROUP_METADATA_CACHE_DATAFRAME]

    def get_partial_aggregate_schema(self):
        return StructType([
            StructField("release_group_name", StringType(), nullable=False),
            StructField("release_group_mbid", StringType(), nullable=False),
            StructField("artist_name", StringType(), nullable=False),
            StructField("artist_credit_mbids", ArrayType(StringType()), nullable=False),
            StructField("caa_id", IntegerType(), nullable=True),
            StructField("caa_release_mbid", StringType(), nullable=True),
            StructField("listen_count", IntegerType(), nullable=False),
        ])

    def aggregate(self, table, cache_tables):
        user_listen_count_limit = self.get_listen_count_limit()
        rel_cache_table = cache_tables[0]
        rg_cache_table = cache_tables[1]
        result = run_query(f"""
        WITH gather_release_group_data AS (
            SELECT l.user_id
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
        ), user_counts as (
            SELECT user_id
                 , first(release_group_name) AS any_release_group_name
                 , release_group_mbid
                 , first(release_group_artist_name) AS any_artist_name
                 , artist_credit_mbids
                 , caa_id
                 , caa_release_mbid
                 , LEAST(count(*), {user_listen_count_limit}) as listen_count
              FROM gather_release_group_data
             WHERE release_group_name != ''
               AND release_group_name IS NOT NULL
          GROUP BY user_id
                 , lower(release_group_name)
                 , release_group_mbid
                 , lower(release_group_artist_name)
                 , artist_credit_mbids
                 , caa_id
                 , caa_release_mbid
        )
            SELECT first(any_release_group_name) AS release_group_name
                 , release_group_mbid
                 , first(any_artist_name) AS artist_name
                 , artist_credit_mbids
                 , caa_id
                 , caa_release_mbid
                 , SUM(listen_count) as listen_count
              FROM user_counts
          GROUP BY lower(any_release_group_name)
                 , release_group_mbid
                 , lower(any_artist_name)
                 , artist_credit_mbids
                 , caa_id
                 , caa_release_mbid
        """)
        return result

    def combine_aggregates(self, existing_aggregate, incremental_aggregate):
        query = f"""
            WITH intermediate_table AS (
                SELECT release_group_name
                     , release_group_mbid
                     , artist_name
                     , artist_credit_mbids
                     , caa_id
                     , caa_release_mbid
                     , listen_count
                  FROM {existing_aggregate}
                 UNION ALL
                SELECT release_group_name
                     , release_group_mbid
                     , artist_name
                     , artist_credit_mbids
                     , caa_id
                     , caa_release_mbid
                     , listen_count
                  FROM {incremental_aggregate}
            )
                SELECT first(release_group_name) AS release_group_name
                     , release_group_mbid
                     , first(artist_name) AS artist_name
                     , artist_credit_mbids
                     , caa_id
                     , caa_release_mbid
                     , sum(listen_count) as total_listen_count
                  FROM intermediate_table
              GROUP BY lower(release_group_name)
                     , release_group_mbid
                     , lower(artist_name)
                     , artist_credit_mbids
                     , caa_id
                     , caa_release_mbid
        """
        return run_query(query)

    def get_top_n(self, final_aggregate, N):
        query = f"""
            WITH entity_count AS (
                SELECT count(*) AS total_count
                  FROM {final_aggregate}
            ), ordered_stats AS (
                SELECT *
                  FROM {final_aggregate}
              ORDER BY total_listen_count DESC
                 LIMIT {N}
            ), grouped_stats AS (
                SELECT sort_array(
                            collect_list(
                                struct(
                                    total_listen_count AS listen_count
                                  , release_group_name
                                  , release_group_mbid
                                  , artist_name
                                  , coalesce(artist_credit_mbids, array()) AS artist_mbids
                                  , caa_id
                                  , caa_release_mbid
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
