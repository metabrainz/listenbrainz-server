from typing import List

from pyspark.sql.types import StructType, StructField, StringType, IntegerType, ArrayType

from listenbrainz_spark.path import RELEASE_METADATA_CACHE_DATAFRAME
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.stats.incremental.sitewide.entity import SitewideEntity


class RecordingSitewideEntity(SitewideEntity):

    def __init__(self, stats_range):
        super().__init__(entity="recordings", stats_range=stats_range)

    def get_cache_tables(self) -> List[str]:
        return [RELEASE_METADATA_CACHE_DATAFRAME]

    def get_partial_aggregate_schema(self):
        return StructType([
            StructField("recording_name", StringType(), nullable=False),
            StructField("recording_mbid", StringType(), nullable=True),
            StructField("artist_name", StringType(), nullable=False),
            StructField("artist_credit_mbids", ArrayType(StringType()), nullable=True),
            StructField("release_name", StringType(), nullable=True),
            StructField("release_mbid", StringType(), nullable=True),
            StructField("caa_id", IntegerType(), nullable=True),
            StructField("caa_release_mbid", StringType(), nullable=True),
            StructField("listen_count", IntegerType(), nullable=False),
        ])

    def aggregate(self, table, cache_tables):
        user_listen_count_limit = self.get_listen_count_limit()
        cache_table = cache_tables[0]
        result = run_query(f"""
        WITH user_counts as (
            SELECT user_id
                 , first(l.recording_name) AS recording_name
                 , nullif(l.recording_mbid, '') AS recording_mbid
                 , first(l.artist_name) AS artist_name
                 , l.artist_credit_mbids
                 , nullif(first(l.release_name), '') as release_name
                 , l.release_mbid
                 , rel.caa_id
                 , rel.caa_release_mbid
                 , LEAST(count(*), {user_listen_count_limit}) as listen_count
              FROM {table} l
         LEFT JOIN {cache_table} rel
                ON rel.release_mbid = l.release_mbid
          GROUP BY l.user_id
                 , lower(l.recording_name)
                 , l.recording_mbid
                 , lower(l.artist_name)
                 , l.artist_credit_mbids
                 , lower(l.release_name)
                 , l.release_mbid
                 , rel.caa_id
                 , rel.caa_release_mbid
        )
            SELECT first(recording_name) AS recording_name
                 , recording_mbid
                 , first(artist_name) AS artist_name
                 , artist_credit_mbids
                 , nullif(first(release_name), '') as release_name
                 , release_mbid
                 , caa_id
                 , caa_release_mbid
                 , SUM(listen_count) as listen_count
              FROM user_counts uc
          GROUP BY lower(uc.recording_name)
                 , recording_mbid
                 , lower(uc.artist_name)
                 , artist_credit_mbids
                 , lower(release_name)
                 , release_mbid
                 , caa_id
                 , caa_release_mbid
        """)
        return result

    def combine_aggregates(self, existing_aggregate, incremental_aggregate):
        query = f"""
            WITH intermediate_table AS (
                SELECT recording_name
                     , recording_mbid
                     , artist_name
                     , artist_credit_mbids
                     , release_name
                     , release_mbid
                     , caa_id
                     , caa_release_mbid
                     , listen_count
                  FROM {existing_aggregate}
                 UNION ALL
                SELECT recording_name
                     , recording_mbid
                     , artist_name
                     , artist_credit_mbids
                     , release_name
                     , release_mbid
                     , caa_id
                     , caa_release_mbid
                     , listen_count
                  FROM {incremental_aggregate}
            )
                SELECT first(recording_name) AS recording_name
                     , recording_mbid
                     , first(artist_name) AS artist_name
                     , artist_credit_mbids
                     , first(release_name) AS release_name
                     , release_mbid
                     , caa_id
                     , caa_release_mbid
                     , sum(listen_count) as listen_count
                  FROM intermediate_table
              GROUP BY lower(recording_name)
                     , recording_mbid
                     , lower(artist_name)
                     , artist_credit_mbids
                     , lower(release_name)
                     , release_mbid
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
              ORDER BY listen_count DESC
                 LIMIT {N}
            ), grouped_stats AS (
                SELECT sort_array(
                            collect_list(
                                struct(
                                        listen_count
                                      , recording_name AS track_name
                                      , recording_mbid
                                      , artist_name
                                      , coalesce(artist_credit_mbids, array()) AS artist_mbids
                                      , release_name
                                      , release_mbid
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
