import logging
from typing import List

from pydantic import ValidationError

from data.model.common_stat_spark import UserStatRecords
from data.model.user_listening_activity import ListeningActivityRecord
from listenbrainz_spark.stats.common.listening_activity import create_time_range_df
from listenbrainz_spark.stats.incremental.range_selector import ListeningActivityListenRangeSelector
from listenbrainz_spark.stats.incremental.user.entity import UserStatsQueryProvider, UserStatsMessageCreator

logger = logging.getLogger(__name__)


class ListeningActivityUserStatsQueryEntity(UserStatsQueryProvider):
    """ See base class QueryProvider for details. """

    def __init__(self, selector: ListeningActivityListenRangeSelector):
        super().__init__(selector)
        self.step, self.date_format, self.spark_date_format = selector.step, selector.date_format, selector.spark_date_format
        create_time_range_df(self.from_date, self.to_date, self.step, self.date_format, self.spark_date_format)

    @property
    def entity(self):
        return "listening_activity"

    def get_cache_tables(self) -> List[str]:
        return []

    def get_aggregate_query(self, table, cache_tables):
        return f"""
            SELECT user_id
                 , date_format(listened_at, '{self.spark_date_format}') AS time_range
                 , count(listened_at) AS listen_count
              FROM {table}
          GROUP BY user_id
                 , time_range
        """

    def get_combine_aggregates_query(self, existing_aggregate, incremental_aggregate):
        return f"""
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

    def get_stats_query(self, final_aggregate):
        return f"""
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


class ListeningActivityUserMessageCreator(UserStatsMessageCreator):

    def __init__(self, message_type: str, selector: ListeningActivityListenRangeSelector, database=None):
        super().__init__("listening_activity", message_type, selector, database)

    def parse_row(self, row):
        try:
            UserStatRecords[ListeningActivityRecord](
                user_id=row["user_id"],
                data=row["listening_activity"]
            )
            return {
                "user_id": row["user_id"],
                "data": row["listening_activity"]
            }
        except ValidationError:
            logger.error("Invalid entry in entity stats:", exc_info=True)