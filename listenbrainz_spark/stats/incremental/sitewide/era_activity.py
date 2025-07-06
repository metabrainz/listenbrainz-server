import logging
from typing import Iterator, Dict

from pyspark.sql import DataFrame

import listenbrainz_spark
from listenbrainz_spark.stats.incremental.message_creator import SitewideStatsMessageCreator
from listenbrainz_spark.stats.incremental.range_selector import ListenRangeSelector, StatsRangeListenRangeSelector
from listenbrainz_spark.stats.incremental.sitewide.entity import SitewideStatsQueryProvider
from listenbrainz_spark.utils import read_files_from_HDFS
from listenbrainz_spark.path import RELEASE_GROUP_METADATA_CACHE_DATAFRAME

logger = logging.getLogger(__name__)


class EraActivitySitewideStatsQuery(SitewideStatsQueryProvider):
    """ Sitewide stats query provider for era activity. """

    def __init__(self, selector: ListenRangeSelector):
        super().__init__(selector)

    @property
    def entity(self):
        return "era_activity"

    def get_aggregate_query(self, table):
        # Load release group metadata and create temp view
        release_groups_df = read_files_from_HDFS(RELEASE_GROUP_METADATA_CACHE_DATAFRAME)
        release_groups_df.createOrReplaceTempView("release_groups")

        return f"""
            SELECT rg.first_release_date_year AS year,
                   COUNT(*) AS listen_count
              FROM {table} l
              LEFT JOIN release_groups rg ON l.release_mbid = rg.caa_release_mbid
             WHERE rg.first_release_date_year IS NOT NULL
          GROUP BY rg.first_release_date_year
        """

    def get_combine_aggregates_query(self, existing_aggregate, incremental_aggregate):
        return f"""
            SELECT year,
                   SUM(listen_count) AS listen_count
              FROM (
                  SELECT year, listen_count
                    FROM {existing_aggregate}
                   UNION ALL
                  SELECT year, listen_count
                    FROM {incremental_aggregate}
              ) combined
          GROUP BY year
        """

    def get_stats_query(self, final_aggregate):
        return f"""
            SELECT SORT_ARRAY(
                       COLLECT_LIST(
                           STRUCT(year, listen_count)
                       )
                   ) AS era_activity
              FROM {final_aggregate}
        """


class EraActivitySitewideMessageCreator(SitewideStatsMessageCreator):
    """ Message creator for sitewide era activity stats. """

    def __init__(self, selector: StatsRangeListenRangeSelector, database=None):
        super().__init__("era_activity", "sitewide_era_activity", selector, database)

    @property
    def default_database_prefix(self):
        return f"{self.entity}_{self.stats_range}"

    def create_messages(self, results: DataFrame, only_inc: bool) -> Iterator[Dict]:
        message = {
            "type": self.message_type,
            "stats_range": self.stats_range,
            "from_ts": int(self.from_date.timestamp()),
            "to_ts": int(self.to_date.timestamp())
        }
        
        # Collect the results and extract the era activity data
        data = results.collect()[0]
        _dict = data.asDict(recursive=True)
        message["data"] = _dict["era_activity"]
        
        logger.info("Created sitewide era activity message for range %s with %d year entries", 
                   self.stats_range, len(message["data"]))
        logger.info(message)
        
        yield message