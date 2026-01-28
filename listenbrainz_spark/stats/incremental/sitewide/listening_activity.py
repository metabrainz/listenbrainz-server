from typing import Iterator, Dict

from pyspark.sql import DataFrame

from listenbrainz_spark.stats.common.listening_activity import create_time_range_df
from listenbrainz_spark.stats.incremental.message_creator import SitewideStatsMessageCreator
from listenbrainz_spark.stats.incremental.range_selector import ListeningActivityListenRangeSelector
from listenbrainz_spark.stats.incremental.sitewide.entity import SitewideStatsQueryProvider


class ListeningActivitySitewideStatsQuery(SitewideStatsQueryProvider):
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
            SELECT date_format(listened_at, '{self.spark_date_format}') AS time_range
                 , count(listened_at) AS listen_count
              FROM {table}
          GROUP BY time_range
        """

    def get_combine_aggregates_query(self, existing_aggregate, incremental_aggregate):
        return f"""
            WITH intermediate_table AS (
                SELECT time_range
                     , listen_count
                  FROM {existing_aggregate}
                 UNION ALL
                SELECT time_range
                     , listen_count
                  FROM {incremental_aggregate}
            )
                SELECT time_range
                     , sum(listen_count) as listen_count
                  FROM intermediate_table
              GROUP BY time_range
        """

    def get_stats_query(self, final_aggregate):
        return f"""
             SELECT sort_array(
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
        """


class ListeningActivitySitewideMessageCreator(SitewideStatsMessageCreator):

    def __init__(self, selector, database=None):
        super().__init__("listening_activty", "sitewide_listening_activity", selector, database)

    def create_messages(self, results: DataFrame, only_inc: bool) -> Iterator[Dict]:
        message = {
            "type": self.message_type,
            "stats_range": self.stats_range,
            "from_ts": int(self.from_date.timestamp()),
            "to_ts": int(self.to_date.timestamp())
        }
        data = results.collect()[0]
        _dict = data.asDict(recursive=True)
        message["data"] = _dict["listening_activity"]
        yield message
