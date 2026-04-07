import logging
from typing import List

from pydantic import ValidationError

import listenbrainz_spark
from data.model.common_stat_spark import UserStatRecords
from data.model.user_era_activity import EraActivityRecord
from listenbrainz_spark.stats.incremental.range_selector import ListenRangeSelector, StatsRangeListenRangeSelector
from listenbrainz_spark.stats.incremental.user.entity import UserStatsQueryProvider, UserStatsMessageCreator
from listenbrainz_spark.utils import read_files_from_HDFS
from listenbrainz_spark.path import RELEASE_GROUP_METADATA_CACHE_DATAFRAME, RELEASE_METADATA_CACHE_DATAFRAME

logger = logging.getLogger(__name__)


class EraActivityUserStatsQueryEntity(UserStatsQueryProvider):
    """ See base class QueryProvider for details. """

    def __init__(self, selector: ListenRangeSelector):
        super().__init__(selector)

    @property
    def entity(self):
        return "era_activity"

    def get_aggregate_query(self, table):
                # Load release group metadata and create temp view
        release_groups_df = read_files_from_HDFS(RELEASE_GROUP_METADATA_CACHE_DATAFRAME)
        release_groups_df.createOrReplaceTempView("release_groups")

        release_df = read_files_from_HDFS(RELEASE_METADATA_CACHE_DATAFRAME)
        release_df.createOrReplaceTempView("release")

        return f"""
            SELECT l.user_id,
                   rg.first_release_date_year AS year,
                   COUNT(*) AS listen_count
            FROM {table} l
            LEFT JOIN release r ON l.release_mbid = r.release_mbid
            LEFT JOIN release_groups rg ON r.release_group_mbid = rg.release_group_mbid
            WHERE rg.first_release_date_year IS NOT NULL
            AND rg.first_release_date_year >= 1800
            GROUP BY l.user_id, rg.first_release_date_year
        """

    def get_combine_aggregates_query(self, existing_aggregate, incremental_aggregate):
        return f"""
            SELECT user_id,
                   year,
                   SUM(listen_count) AS listen_count
              FROM (
                  SELECT user_id, year, listen_count
                    FROM {existing_aggregate}
                   UNION ALL
                  SELECT user_id, year, listen_count
                    FROM {incremental_aggregate}
              ) combined
          GROUP BY user_id, year
        """

    def get_stats_query(self, final_aggregate):
        return f"""
            SELECT user_id,
                   SORT_ARRAY(
                       COLLECT_LIST(
                           STRUCT(year, listen_count)
                       )
                   ) AS era_activity
              FROM {final_aggregate}
          GROUP BY user_id
        """


class EraActivityUserMessageCreator(UserStatsMessageCreator):

    def __init__(self, message_type: str, selector: StatsRangeListenRangeSelector, database=None):
        super().__init__("era_activity", message_type, selector, database)

    @property
    def default_database_prefix(self):
        return f"{self.entity}_{self.stats_range}"

    def parse_row(self, entry: dict):
        try:
            UserStatRecords[EraActivityRecord](
                user_id=entry["user_id"],
                data=entry["era_activity"]
            )
            return {
                "user_id": entry["user_id"],
                "data": entry["era_activity"]
            }
        except ValidationError:
            logger.error("Invalid entry in era activity stats for user %s", 
                        entry.get("user_id", "unknown"), exc_info=True)
            return None