from typing import List

from pyspark.sql.types import StructType, StructField, StringType, IntegerType

from listenbrainz_spark.path import ARTIST_COUNTRY_CODE_DATAFRAME
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.stats.incremental.user.entity import UserEntity


class ArtistUserEntity(UserEntity):

    def __init__(self):
        super().__init__(entity="artists")

    def get_cache_tables(self) -> List[str]:
        return [ARTIST_COUNTRY_CODE_DATAFRAME]

    def get_partial_aggregate_schema(self):
        return StructType([
            StructField('user_id', IntegerType(), nullable=False),
            StructField('artist_name', StringType(), nullable=False),
            StructField('artist_mbid', StringType(), nullable=True),
            StructField('listen_count', IntegerType(), nullable=False),
        ])

    def aggregate(self, table, cache_tables):
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
                SELECT user_id
                -- we group by lower(artist_name) and pick the first artist name for cases where
                -- the artist name differs in case. for mapped listens the artist name from MB will
                -- be used. for unmapped listens we can't know which case is correct so use any. note
                -- that due to presence of artist mbid as the third group, mapped and unmapped listens
                -- will always be separately grouped therefore first will work fine for unmapped
                -- listens and doesn't matter for mapped ones.
                     , first(artist_name) AS artist_name
                     , artist_mbid
                     , count(*) AS listen_count
                 FROM listens_with_mb_data
             GROUP BY user_id
                    , lower(artist_name)
                    , artist_mbid
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
                SELECT first(artist_name) AS artist_name
                     , artist_mbid
                     , sum(listen_count) as total_listen_count
                  FROM intermediate_table
              GROUP BY lower(artist_name)
                     , artist_mbid
        """
        return run_query(query)

    def get_top_n(self, final_aggregate, N):
        query = f"""
            WITH entity_count AS (
                SELECT user_id
                     , count(*) AS total_count
                  FROM {final_aggregate}
              GROUP BY user_id
            ), ranked_stats AS (
                SELECT user_id
                     , artist_name
                     , artist_mbid
                     , listen_count
                     , row_number() OVER (PARTITION BY user_id ORDER BY listen_count DESC) AS rank
                  FROM {final_aggregate}
            ), grouped_stats AS (
                SELECT user_id
                     , sort_array(
                            collect_list(
                                struct(
                                    listen_count
                                  , artist_name
                                  , artist_mbid
                                )
                            )
                            , false
                       ) as artists
                  FROM ranked_stats
                 WHERE rank <= {N}
              GROUP BY user_id
            )
                SELECT user_id
                     , artists_count
                     , artists
                  FROM grouped_stats
                  JOIN entity_count
                 USING (user_id)
        """
        return run_query(query)
