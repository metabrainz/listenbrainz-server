import logging
from typing import List

from pydantic import ValidationError
from pyspark.sql.types import StructType, StructField, StringType, IntegerType

from data.model.common_stat_spark import UserStatRecords
from data.model.user_listening_activity import ListeningActivityRecord
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.stats.common.listening_activity import setup_time_range
from listenbrainz_spark.stats.incremental.user.entity import UserEntity

logger = logging.getLogger(__name__)


class ListeningActivityUserEntity(UserEntity):

    def __init__(self, stats_range, database, message_type, year=None):
        super().__init__(
            entity="listening_activity", stats_range=stats_range,
            database=database, message_type=message_type
        )
        self.year = year
        self.from_date, self.to_date, _, __, self.spark_date_format = setup_time_range(self.stats_range, self.year)

    def get_cache_tables(self) -> List[str]:
        return []

    def get_partial_aggregate_schema(self):
        return StructType([
            StructField("user_id", IntegerType(), nullable=False),
            StructField("time_range", StringType(), nullable=False),
            StructField("listen_count", IntegerType(), nullable=False),
        ])

    def aggregate(self, table, cache_tables):
        result = run_query(f"""
            SELECT user_id
                 , date_format(listened_at, '{self.spark_date_format}') AS time_range
                 , count(listened_at) AS listen_count
              FROM {table}
          GROUP BY user_id
                 , time_range
        """)
        return result

    def combine_aggregates(self, existing_aggregate, incremental_aggregate):
        query = f"""
            WITH intermediate_table AS (
                SELECT user_id
                     , time_range
                     , listen_count
                  FROM {existing_aggregate}
                 UNION ALL
                SELECT user_id
                     , time_range
                     , listen_count
                  FROM {incremental_aggregate}
            )
                SELECT user_id
                     , time_range
                     , sum(listen_count) as listen_count
                  FROM intermediate_table
              GROUP BY user_id
                     , time_range
        """
        return run_query(query)

    def get_top_n(self, final_aggregate, N):
        query = f"""
             SELECT user_id
                  , sort_array(
                       collect_list(
                            struct(
                                  to_unix_timestamp(start) AS from_ts
                                , to_unix_timestamp(end) AS to_ts
                                , time_range
                                , COALESCE(listen_count, 0) AS listen_count
                            )
                        )
                    ) AS listening_activity
               FROM time_range
          LEFT JOIN {final_aggregate}
              USING (time_range)
           GROUP BY user_id
        """
        return run_query(query)

    def parse_one_user_stats(self, entry: dict):
        try:
            UserStatRecords[ListeningActivityRecord](
                user_id=entry["user_id"],
                data=entry["listening_activity"]
            )
            return {
                "user_id": entry["user_id"],
                "data": entry["listening_activity"]
            }
        except ValidationError:
            logger.error("Invalid entry in entity stats:", exc_info=True)
