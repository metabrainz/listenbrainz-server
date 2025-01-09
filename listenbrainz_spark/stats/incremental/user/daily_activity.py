import calendar
import itertools
import json
import logging
from typing import List

from pydantic import ValidationError
from pyspark.sql.types import StructType, StructField, StringType, IntegerType

import listenbrainz_spark
from data.model.common_stat_spark import UserStatRecords
from data.model.user_daily_activity import DailyActivityRecord
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.stats.incremental.user.entity import UserEntity

logger = logging.getLogger(__name__)


class DailyActivityUserEntity(UserEntity):

    def  __init__(self, stats_range, database, message_type):
        super().__init__(entity="daily_activity", stats_range=stats_range, database=database, message_type=message_type)
        self.setup_time_range()

    def setup_time_range(self):
        # Genarate a dataframe containing hours of all days of the week
        weekdays = [calendar.day_name[day] for day in range(0, 7)]
        hours = [hour for hour in range(0, 24)]
        time_range = itertools.product(weekdays, hours)
        time_range_df = listenbrainz_spark.session.createDataFrame(time_range, schema=["day", "hour"])
        time_range_df.createOrReplaceTempView("time_range")

    def get_cache_tables(self) -> List[str]:
        return []

    def get_partial_aggregate_schema(self):
        return StructType([
            StructField("user_id", IntegerType(), nullable=False),
            StructField("day", StringType(), nullable=False),
            StructField("hour", IntegerType(), nullable=False),
            StructField("listen_count", IntegerType(), nullable=False),
        ])

    def aggregate(self, table, cache_tables):
        result = run_query(f"""
            SELECT user_id
                 , date_format(listened_at, 'EEEE') as day
                 , date_format(listened_at, 'H') as hour
                 , count(listened_at) AS listen_count
              FROM {table}
          GROUP BY user_id
                 , day
                 , hour
        """)
        return result

    def combine_aggregates(self, existing_aggregate, incremental_aggregate):
        query = f"""
            WITH intermediate_table AS (
                SELECT user_id
                     , day
                     , hour
                     , listen_count
                  FROM {existing_aggregate}
                 UNION ALL
                SELECT user_id
                     , day
                     , hour
                     , listen_count
                  FROM {incremental_aggregate}
            )
                SELECT user_id
                     , day
                     , hour
                     , sum(listen_count) as listen_count
                  FROM intermediate_table
              GROUP BY user_id
                     , day
                     , hour
        """
        return run_query(query)

    def get_top_n(self, final_aggregate, N):
        query = f"""
             SELECT user_id
                  , sort_array(
                       collect_list(
                            struct(
                                  day
                                , hour
                                , COALESCE(listen_count, 0) AS listen_count
                            )
                        )
                    ) AS daily_activity
               FROM time_range
          LEFT JOIN {final_aggregate}
              USING (day, hour)
           GROUP BY user_id
        """
        return run_query(query)

    def parse_one_user_stats(self, entry: dict):
        try:
            UserStatRecords[DailyActivityRecord](
                user_id=entry["user_id"],
                data=entry["daily_activity"]
            )
            return {
                "user_id": entry["user_id"],
                "data": entry["daily_activity"]
            }
        except ValidationError:
            logger.error("Invalid entry in entity stats:", exc_info=True)
