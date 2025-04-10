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

    def get_aggregate_query(self, table):
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
        # calculates the number of listens in each time range for each user, count(listen.listened_at) so that
        # group without listens are counted as 0, count(*) gives 1.
        # use cross join to create all time range rows for all users (otherwise ranges in which user was inactive
        # would be missing from final output)
        return f"""
           WITH dist_user_id AS (
               SELECT DISTINCT user_id FROM {final_aggregate}
           )
               SELECT d.user_id AS user_id
                    , sort_array(
                        collect_list(
                            struct(
                                  to_unix_timestamp(tr.start) AS from_ts
                                , to_unix_timestamp(tr.end) AS to_ts
                                , tr.time_range AS time_range
                                , COALESCE(fa.listen_count, 0) AS listen_count
                            )
                        )
                      ) AS listening_activity
                 FROM dist_user_id d
           CROSS JOIN time_range tr
            LEFT JOIN {final_aggregate} fa
                   ON fa.time_range = tr.time_range
                  AND fa.user_id = d.user_id
             GROUP BY d.user_id
        """


class ListeningActivityUserMessageCreator(UserStatsMessageCreator):

    def __init__(self, message_type: str, selector: ListeningActivityListenRangeSelector, database=None):
        super().__init__("listening_activity", message_type, selector, database)

    @property
    def default_database_prefix(self):
        return f"{self.entity}_{self.stats_range}"

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