from typing import List

from pyspark.sql.types import StructType, StructField, StringType, IntegerType, ArrayType

from listenbrainz_spark.path import ARTIST_COUNTRY_CODE_DATAFRAME, RELEASE_METADATA_CACHE_DATAFRAME, \
    RELEASE_GROUP_METADATA_CACHE_DATAFRAME
from listenbrainz_spark.schema import artists_column_schema
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.stats.incremental.user.entity import UserEntity


class ReleaseGroupUserEntity(UserEntity):
    """ See base class IncrementalStats for documentation. """

    def __init__(self, stats_range, database, message_type, from_date=None, to_date=None):
        super().__init__(entity="release_groups", stats_range=stats_range, database=database, message_type=message_type,
                         from_date=from_date, to_date=to_date)

    def get_cache_tables(self) -> List[str]:
        return [RELEASE_METADATA_CACHE_DATAFRAME, RELEASE_GROUP_METADATA_CACHE_DATAFRAME]

    def get_partial_aggregate_schema(self):
        return StructType([
            StructField("user_id", IntegerType(), nullable=False),
            StructField("release_group_name", StringType(), nullable=False),
            StructField("release_group_mbid", StringType(), nullable=False),
            StructField("artist_name", StringType(), nullable=False),
            StructField("artist_credit_mbids", ArrayType(StringType()), nullable=False),
            StructField("artists", artists_column_schema, nullable=True),
            StructField("caa_id", IntegerType(), nullable=True),
            StructField("caa_release_mbid", StringType(), nullable=True),
            StructField("listen_count", IntegerType(), nullable=False),
        ])

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
                     , rg.artists
                     , rg.caa_id
                     , rg.caa_release_mbid
                  FROM {table} l
             LEFT JOIN {rel_cache_table} rel
                    ON rel.release_mbid = l.release_mbid
             LEFT JOIN {rg_cache_table} rg
                    ON rg.release_group_mbid = rel.release_group_mbid
            )
                SELECT user_id
                     , first(release_group_name) AS release_group_name
                     , release_group_mbid
                     , first(release_group_artist_name) AS artist_name
                     , artist_credit_mbids
                     , caa_id
                     , caa_release_mbid
                     , artists
                     , count(*) as listen_count
                  FROM gather_release_data
                 WHERE release_group_name != ''
                   AND release_group_name IS NOT NULL
              GROUP BY user_id
                     , lower(release_group_name)
                     , release_group_mbid
                     , lower(release_group_artist_name)
                     , artist_credit_mbids
                     , caa_id
                     , caa_release_mbid
                     , artists
        """)
        return result

    def combine_aggregates(self, existing_aggregate, incremental_aggregate):
        query = f"""
            WITH intermediate_table AS (
                SELECT user_id
                     , release_group_name
                     , release_group_mbid
                     , artist_name
                     , artist_credit_mbids
                     , artists
                     , caa_id
                     , caa_release_mbid
                     , listen_count
                  FROM {existing_aggregate}
                 UNION ALL
                SELECT user_id
                     , release_group_name
                     , release_group_mbid
                     , artist_name
                     , artist_credit_mbids
                     , artists
                     , caa_id
                     , caa_release_mbid
                     , listen_count
                  FROM {incremental_aggregate}
            )
                SELECT user_id
                     , first(release_group_name) AS release_group_name
                     , release_group_mbid
                     , first(artist_name) AS artist_name
                     , artist_credit_mbids
                     , artists
                     , caa_id
                     , caa_release_mbid
                     , sum(listen_count) as listen_count
                  FROM intermediate_table
              GROUP BY user_id
                     , lower(release_group_name)
                     , release_group_mbid
                     , lower(artist_name)
                     , artist_credit_mbids
                     , artists
                     , caa_id
                     , caa_release_mbid
        """
        return run_query(query)

    def get_top_n(self, final_aggregate, N):
        query = f"""
            WITH entity_count AS (
                SELECT user_id
                     , count(*) AS release_groups_count
                  FROM {final_aggregate}
              GROUP BY user_id
            ), ranked_stats AS (
                SELECT user_id
                     , release_group_name
                     , release_group_mbid
                     , artist_name
                     , artist_credit_mbids
                     , artists
                     , caa_id
                     , caa_release_mbid
                     , listen_count
                     , row_number() OVER (PARTITION BY user_id ORDER BY listen_count DESC) AS rank
                  FROM {final_aggregate}
            ), grouped_stats AS (
                SELECT user_id
                     , sort_array(
                            collect_list(
                                struct(
                                    listen_count
                                  , release_group_name
                                  , release_group_mbid
                                  , artist_name
                                  , coalesce(artist_credit_mbids, array()) AS artist_mbids
                                  , artists
                                  , caa_id
                                  , caa_release_mbid
                                )
                            )
                            , false
                       ) as release_groups
                  FROM ranked_stats
                 WHERE rank <= {N}
              GROUP BY user_id
            )
                SELECT user_id
                     , release_groups_count
                     , release_groups
                  FROM grouped_stats
                  JOIN entity_count
                 USING (user_id)
        """
        return run_query(query)
