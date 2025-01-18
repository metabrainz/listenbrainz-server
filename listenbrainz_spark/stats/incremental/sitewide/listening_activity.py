from typing import List, Iterator, Dict

from pyspark.sql import DataFrame
from pyspark.sql.types import StructType, StructField, StringType, IntegerType

from listenbrainz_spark.stats import run_query
from listenbrainz_spark.stats.common.listening_activity import setup_time_range
from listenbrainz_spark.stats.incremental.sitewide.entity import SitewideEntity


class ListeningActivitySitewideEntity(SitewideEntity):

    def __init__(self, stats_range):
        super().__init__(entity="listening_activity", stats_range=stats_range)
        self.from_date, self.to_date, _, __, self.spark_date_format = setup_time_range(stats_range)

    def get_cache_tables(self) -> List[str]:
        return []

    def get_partial_aggregate_schema(self):
        return StructType([
            StructField("time_range", StringType(), nullable=False),
            StructField("listen_count", IntegerType(), nullable=False),
        ])

    def aggregate(self, table, cache_tables):
        result = run_query(f"""
            SELECT date_format(listened_at, '{self.spark_date_format}') AS time_range
                 , count(listened_at) AS listen_count
              FROM {table}
          GROUP BY time_range
        """)
        return result

    def combine_aggregates(self, existing_aggregate, incremental_aggregate):
        query = f"""
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
        return run_query(query)

    def get_top_n(self, final_aggregate, N):
        query = f"""
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
        return run_query(query)

    def create_messages(self, results: DataFrame) -> Iterator[Dict]:
        message = {
            "type": "sitewide_listening_activity",
            "stats_range": self.stats_range,
            "from_ts": int(self.from_date.timestamp()),
            "to_ts": int(self.to_date.timestamp())
        }
        data = results.collect()[0]
        _dict = data.asDict(recursive=True)
        message["data"] = _dict["listening_activity"]
        yield message
