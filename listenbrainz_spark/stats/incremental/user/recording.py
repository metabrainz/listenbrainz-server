from typing import List

from pyspark.sql.types import StructType, StructField, StringType, IntegerType, ArrayType

from listenbrainz_spark.path import ARTIST_COUNTRY_CODE_DATAFRAME, RECORDING_ARTIST_DATAFRAME, \
    RELEASE_METADATA_CACHE_DATAFRAME
from listenbrainz_spark.schema import artists_column_schema
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.stats.incremental.user.entity import UserEntity


class RecordingUserEntity(UserEntity):
    """ See base class IncrementalStats for documentation. """

    def __init__(self, stats_range, database, message_type, from_date=None, to_date=None):
        super().__init__(entity="recordings", stats_range=stats_range, database=database, message_type=message_type,
                         from_date=from_date, to_date=to_date)

    def get_cache_tables(self) -> List[str]:
        return [RECORDING_ARTIST_DATAFRAME, RELEASE_METADATA_CACHE_DATAFRAME]

    def get_partial_aggregate_schema(self):
        return StructType([
            StructField("user_id", IntegerType(), nullable=False),
            StructField("recording_name", StringType(), nullable=False),
            StructField("recording_mbid", StringType(), nullable=True),
            StructField("artist_name", StringType(), nullable=False),
            StructField("artist_credit_mbids", ArrayType(StringType()), nullable=True),
            StructField("release_name", StringType(), nullable=True),
            StructField("release_mbid", StringType(), nullable=True),
            StructField("artists", artists_column_schema, nullable=True),
            StructField("caa_id", IntegerType(), nullable=True),
            StructField("caa_release_mbid", StringType(), nullable=True),
            StructField("listen_count", IntegerType(), nullable=False),
        ])

    def aggregate(self, table, cache_tables):
        rec_cache_table = cache_tables[0]
        rel_cache_table = cache_tables[1]
        result = run_query(f"""
            SELECT user_id
                 , first(l.recording_name) AS recording_name
                 , nullif(l.recording_mbid, '') AS recording_mbid
                 , first(l.artist_name) AS artist_name
                 , l.artist_credit_mbids
                 , nullif(first(l.release_name), '') as release_name
                 , nullif(l.release_mbid, '') AS release_mbid
                 , rec.artists
                 , rel.caa_id
                 , rel.caa_release_mbid
                 , count(*) as listen_count
              FROM {table} l
         LEFT JOIN {rec_cache_table} rec
                ON rec.recording_mbid = l.recording_mbid
         LEFT JOIN {rel_cache_table} rel
                ON rel.release_mbid = l.release_mbid
          GROUP BY l.user_id
                 , lower(l.recording_name)
                 , l.recording_mbid
                 , lower(l.artist_name)
                 , l.artist_credit_mbids
                 , lower(l.release_name)
                 , l.release_mbid
                 , rec.artists
                 , rel.caa_id
                 , rel.caa_release_mbid
        """)
        return result

    def combine_aggregates(self, existing_aggregate, incremental_aggregate):
        query = f"""
            WITH intermediate_table AS (
                SELECT user_id
                     , recording_name
                     , recording_mbid
                     , artist_name
                     , artist_credit_mbids
                     , release_name
                     , release_mbid
                     , artists
                     , caa_id
                     , caa_release_mbid
                     , listen_count
                  FROM {existing_aggregate}
                 UNION ALL
                SELECT user_id
                     , recording_name
                     , recording_mbid
                     , artist_name
                     , artist_credit_mbids
                     , release_name
                     , release_mbid
                     , artists
                     , caa_id
                     , caa_release_mbid
                     , listen_count
                  FROM {incremental_aggregate}
            )
                SELECT user_id
                     , first(recording_name) AS recording_name
                     , recording_mbid
                     , first(artist_name) AS artist_name
                     , artist_credit_mbids
                     , first(release_name) AS release_name
                     , release_mbid
                     , artists
                     , caa_id
                     , caa_release_mbid
                     , sum(listen_count) as listen_count
                  FROM intermediate_table
              GROUP BY user_id
                     , lower(recording_name)
                     , recording_mbid
                     , lower(artist_name)
                     , artist_credit_mbids
                     , lower(release_name)
                     , release_mbid
                     , artists
                     , caa_id
                     , caa_release_mbid
        """
        return run_query(query)

    def get_top_n(self, final_aggregate, N):
        query = f"""
            WITH entity_count AS (
                SELECT user_id
                     , count(*) AS recordings_count
                  FROM {final_aggregate}
              GROUP BY user_id
            ), ranked_stats AS (
                SELECT user_id
                     , recording_name as track_name
                     , recording_mbid
                     , release_name
                     , release_mbid
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
                                  , track_name
                                  , recording_mbid
                                  , artist_name
                                  , coalesce(artist_credit_mbids, array()) AS artist_mbids
                                  , release_name
                                  , release_mbid
                                  , artists
                                  , caa_id
                                  , caa_release_mbid
                                )
                            )
                            , false
                       ) as recordings
                  FROM ranked_stats
                 WHERE rank <= {N}
              GROUP BY user_id
            )
                SELECT user_id
                     , recordings_count
                     , recordings
                  FROM grouped_stats
                  JOIN entity_count
                 USING (user_id)
        """
        return run_query(query)
