import itertools
import logging
from typing import List

from pydantic import ValidationError

import listenbrainz_spark
from data.model.common_stat_spark import UserStatRecords
from data.model.user_genre_activity import GenreActivityRecord
from listenbrainz_spark.stats.incremental.range_selector import ListenRangeSelector, StatsRangeListenRangeSelector
from listenbrainz_spark.stats.incremental.user.entity import UserStatsQueryProvider, UserStatsMessageCreator

logger = logging.getLogger(__name__)


class GenreActivityUserStatsQueryEntity(UserStatsQueryProvider):
    """ See base class QueryProvider for details. """

    def __init__(self, selector: ListenRangeSelector):
        super().__init__(selector)
        self.setup_time_brackets()

    @property
    def entity(self):
        return "genre_trend"

    def setup_time_brackets(self):
        """ Generate a dataframe containing time brackets for genre analysis. """
        time_brackets = ['00-06', '06-12', '12-18', '18-24']
        time_brackets_df = listenbrainz_spark.session.createDataFrame(
            [(bracket,) for bracket in time_brackets], 
            schema=["time_bracket"]
        )
        time_brackets_df.createOrReplaceTempView("time_brackets")

    def get_aggregate_query(self, table):
        return f"""
            WITH genre_listens AS (
                SELECT l.user_id
                     , g.genre
                     , CASE
                           WHEN HOUR(l.listened_at) < 6 THEN '00-06'
                           WHEN HOUR(l.listened_at) < 12 THEN '06-12'
                           WHEN HOUR(l.listened_at) < 18 THEN '12-18'
                           ELSE '18-24'
                       END AS time_bracket
                     , COUNT(*) AS listen_count
                  FROM {table} l
                  LEFT JOIN genres g ON l.recording_mbid = g.recording_mbid
                 WHERE g.genre IS NOT NULL
              GROUP BY l.user_id
                     , g.genre
                     , time_bracket
            )
            SELECT user_id
                 , genre
                 , time_bracket
                 , listen_count
              FROM genre_listens
        """

    def get_combine_aggregates_query(self, existing_aggregate, incremental_aggregate):
        return f"""
            WITH intermediate_table AS (
                SELECT user_id
                     , genre
                     , time_bracket
                     , listen_count
                  FROM {existing_aggregate}
                 UNION ALL
                SELECT user_id
                     , genre
                     , time_bracket
                     , listen_count
                  FROM {incremental_aggregate}
            )
                SELECT user_id
                     , genre
                     , time_bracket
                     , sum(listen_count) as listen_count
                  FROM intermediate_table
              GROUP BY user_id
                     , genre
                     , time_bracket
        """

    def get_stats_query(self, final_aggregate):
        return f"""
            WITH all_genre_time_combinations AS (
                SELECT DISTINCT user_id, genre, time_bracket
                  FROM {final_aggregate}
                 CROSS JOIN time_brackets
            )
            SELECT user_id
                 , sort_array(
                      collect_list(
                           struct(
                                 genre
                               , time_bracket
                               , COALESCE(fa.listen_count, 0) AS listen_count
                           )
                       )
                   ) AS genre_trend
              FROM all_genre_time_combinations agtc
         LEFT JOIN {final_aggregate} fa
                ON agtc.user_id = fa.user_id 
               AND agtc.genre = fa.genre 
               AND agtc.time_bracket = fa.time_bracket
          GROUP BY user_id
        """


class GenreActivityUserMessageCreator(UserStatsMessageCreator):

    def __init__(self, message_type: str, selector: StatsRangeListenRangeSelector, database=None):
        super().__init__("genre_trend", message_type, selector, database)

    @property
    def default_database_prefix(self):
        return f"{self.entity}_{self.stats_range}"

    def parse_row(self, entry: dict):
        try:
            UserStatRecords[GenreActivityRecord](
                user_id=entry["user_id"],
                data=entry["genre_trend"]
            )
            return {
                "user_id": entry["user_id"],
                "data": entry["genre_trend"]
            }
        except ValidationError:
            logger.error("Invalid entry in genre trend stats:", exc_info=True)
