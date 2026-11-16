import logging
from typing import List

from pydantic import ValidationError, BaseModel, NonNegativeInt, constr

import listenbrainz_spark
from data.model.common_stat_spark import UserStatRecords
from listenbrainz_spark.listens.cache import *
from listenbrainz_spark.listens.metadata import *
from listenbrainz_spark import config, hdfs_connection
from data.model.user_artist_evolution_activity import ArtistEvolutionActivityRecord
from listenbrainz_spark.stats.incremental.range_selector import ListenRangeSelector, StatsRangeListenRangeSelector
from listenbrainz_spark.stats.incremental.user.entity import UserStatsQueryProvider, UserStatsMessageCreator
from listenbrainz_spark.utils import read_files_from_HDFS
from listenbrainz_spark.path import RECORDING_ARTIST_DATAFRAME

logger = logging.getLogger(__name__)


class ArtistEvolutionActivityUserStatsQueryEntity(UserStatsQueryProvider):
    """ See base class QueryProvider for details. """

    def __init__(self, selector: ListenRangeSelector, top_n: int):
        super().__init__(selector)
        self.stats_range = selector.stats_range
        self.top_n = top_n

    @property
    def entity(self):
        return "artist_evolution_activity"

    def _get_time_field_expression(self):
        if self.stats_range in ("week", "this_week"):
            return "((dayofweek(listened_at) + 5) % 7) + 1"
        elif self.stats_range in ("month", "this_month"):
            return "day(listened_at)"
        elif self.stats_range in ("year", "half_yearly", "quarter", "this_year"):
            return "month(listened_at)"
        else:
            return "year(listened_at)"

    def get_aggregate_query(self, table):
        recording_df = read_files_from_HDFS(RECORDING_ARTIST_DATAFRAME)
        recording_df.createOrReplaceTempView("recording_artist")
        time_field = self._get_time_field_expression()
        return f"""
            SELECT l.user_id
                 , {time_field} AS time_unit
                 , artist_element.artist_mbid AS artist_mbid
                 , artist_element.artist_credit_name AS artist_name
                 , COUNT(*) AS listen_count
              FROM {table} l
              JOIN recording_artist ra ON l.recording_mbid = ra.recording_mbid
            LATERAL VIEW explode(ra.artists) AS artist_element
          GROUP BY l.user_id
                 , {time_field}
                 , artist_element.artist_mbid
                 , artist_element.artist_credit_name
        """

    def get_combine_aggregates_query(self, existing_aggregate, incremental_aggregate):
        return f"""
            WITH intermediate_table AS (
                SELECT user_id
                     , time_unit
                     , artist_mbid
                     , artist_name
                     , listen_count
                  FROM {existing_aggregate}
                 UNION ALL
                SELECT user_id
                     , time_unit
                     , artist_mbid
                     , artist_name
                     , listen_count
                  FROM {incremental_aggregate}
            )
                SELECT user_id
                     , time_unit
                     , artist_mbid
                     , artist_name
                     , sum(listen_count) as listen_count
                  FROM intermediate_table
              GROUP BY user_id
                     , time_unit
                     , artist_mbid
                     , artist_name
        """

    def get_stats_query(self, final_aggregate):
        return f"""
               WITH total_artist_listens AS (
                    SELECT user_id
                         , artist_mbid
                         , artist_name
                         , SUM(listen_count) AS total_listens
                      FROM {final_aggregate}
                  GROUP BY user_id, artist_mbid, artist_name
                ), top_artists AS (
                    SELECT user_id
                         , artist_mbid
                         , artist_name
                         , ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY total_listens DESC) AS rank
                      FROM total_artist_listens
                )    SELECT f.user_id
                          , sort_array(
                                   collect_list(
                                        struct(
                                              f.time_unit
                                            , f.artist_mbid
                                            , f.artist_name
                                            , f.listen_count
                                        )
                                    ), false
                            ) AS artist_evolution_activity
                       FROM {final_aggregate} f
                       JOIN top_artists ta 
                         ON f.user_id = ta.user_id 
                        AND (f.artist_mbid = ta.artist_mbid OR (f.artist_mbid IS NULL AND ta.artist_mbid IS NULL))
                        AND f.artist_name = ta.artist_name
                      WHERE ta.rank <= {self.top_n}
                   GROUP BY f.user_id
         """

class ArtistEvolutionActivityUserMessageCreator(UserStatsMessageCreator):

    def __init__(self, message_type: str, selector: StatsRangeListenRangeSelector, database=None):
        super().__init__("artist_evolution_activity", message_type, selector, database)

    @property
    def default_database_prefix(self):
        return f"{self.entity}_{self.stats_range}"

    def parse_row(self, entry: dict):
        try:
            UserStatRecords[ArtistEvolutionActivityRecord](
                user_id=entry["user_id"],
                data=entry["artist_evolution_activity"]
            )
            return {
                "user_id": entry["user_id"],
                "data": entry["artist_evolution_activity"]
            }
        except ValidationError:
            logger.error("Invalid entry in artist evolution stats for user %s", 
                        entry.get("user_id", "unknown"), exc_info=True)
            return None