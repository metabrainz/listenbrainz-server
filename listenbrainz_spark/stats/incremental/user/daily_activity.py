import calendar
import itertools
import logging
from typing import List

from pydantic import ValidationError

import listenbrainz_spark
from data.model.common_stat_spark import UserStatRecords
from data.model.user_daily_activity import DailyActivityRecord
from listenbrainz_spark.stats.incremental.range_selector import ListenRangeSelector, StatsRangeListenRangeSelector
from listenbrainz_spark.stats.incremental.user.entity import UserStatsQueryProvider, UserStatsMessageCreator

logger = logging.getLogger(__name__)


class DailyActivityUserStatsQueryEntity(UserStatsQueryProvider):
    """ See base class QueryProvider for details. """

    def __init__(self, selector: ListenRangeSelector):
        super().__init__(selector)
        self.setup_time_range()

    @property
    def entity(self):
        return "daily_activity"

    def setup_time_range(self):
        """ Genarate a dataframe containing hours of all days of the week. """
        weekdays = [calendar.day_name[day] for day in range(0, 7)]
        hours = [hour for hour in range(0, 24)]
        time_range = itertools.product(weekdays, hours)
        time_range_df = listenbrainz_spark.session.createDataFrame(time_range, schema=["day", "hour"])
        time_range_df.createOrReplaceTempView("time_range")

    def get_aggregate_query(self, table):
        return f"""
            SELECT user_id
                 , date_format(listened_at, 'EEEE') as day
                 , date_format(listened_at, 'H') as hour
                 , count(listened_at) AS listen_count
              FROM {table}
          GROUP BY user_id
                 , day
                 , hour
        """

    def get_combine_aggregates_query(self, existing_aggregate, incremental_aggregate):
        return f"""
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

    def get_stats_query(self, final_aggregate):
        return f"""
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
              WHERE user_id IS NOT NULL
           GROUP BY user_id
        """


class DailyActivityUserMessageCreator(UserStatsMessageCreator):

    def __init__(self, message_type: str, selector: StatsRangeListenRangeSelector, database=None):
        super().__init__("daily_activity", message_type, selector, database)

    @property
    def default_database_prefix(self):
        return f"{self.entity}_{self.stats_range}"

    def parse_row(self, entry: dict):
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
