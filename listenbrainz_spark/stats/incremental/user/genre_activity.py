import itertools
import logging
from typing import List

from pydantic import ValidationError

import listenbrainz_spark
from data.model.common_stat_spark import UserStatRecords
from data.model.user_genre_activity import GenreActivityRecord
from listenbrainz_spark.stats.incremental.range_selector import ListenRangeSelector, StatsRangeListenRangeSelector
from listenbrainz_spark.stats.incremental.user.entity import UserStatsQueryProvider, UserStatsMessageCreator

from listenbrainz_spark.utils import read_files_from_HDFS
from listenbrainz_spark.path import RECORDING_RECORDING_GENRE_DATAFRAME

logger = logging.getLogger(__name__)


class GenreActivityUserStatsQueryEntity(UserStatsQueryProvider):
    """ See base class QueryProvider for details. """

    def __init__(self, selector: ListenRangeSelector):
        super().__init__(selector)
        self.setup_hours()

    @property
    def entity(self):
        return "genre_activity"

    def setup_hours(self):
        """ Generate a dataframe containing hourly time brackets for genre analysis. """
        hours = [f"{hour:02d}" for hour in range(24)]
        hours_df = listenbrainz_spark.session.createDataFrame(
            [(bracket,) for bracket in hours], 
            schema=["hour"]
        )
        hours_df.createOrReplaceTempView("hours")

    def get_aggregate_query(self, table):
        genres_df = read_files_from_HDFS(RECORDING_RECORDING_GENRE_DATAFRAME)
        genres_df.createOrReplaceTempView("genres")
        return f"""
            WITH genre_listens AS (
                SELECT l.user_id
                     , g.genre
                     , LPAD(HOUR(l.listened_at), 2, '0') AS hour
                     , COUNT(*) AS listen_count
                  FROM {table} l
                  LEFT JOIN genres g ON l.recording_mbid = g.recording_mbid
                 WHERE g.genre IS NOT NULL
              GROUP BY l.user_id
                     , g.genre
                     , LPAD(HOUR(l.listened_at), 2, '0')
            )
            SELECT user_id
                 , genre
                 , hour
                 , listen_count
              FROM genre_listens
        """

    def get_combine_aggregates_query(self, existing_aggregate, incremental_aggregate):
        return f"""
            WITH intermediate_table AS (
                SELECT user_id
                     , genre
                     , hour
                     , listen_count
                  FROM {existing_aggregate}
                 UNION ALL
                SELECT user_id
                     , genre
                     , hour
                     , listen_count
                  FROM {incremental_aggregate}
            )
                SELECT user_id
                     , genre
                     , hour
                     , sum(listen_count) as listen_count
                  FROM intermediate_table
              GROUP BY user_id
                     , genre
                     , hour
        """

    def get_stats_query(self, final_aggregate):
        return f"""
			WITH ranked_genres AS (
				SELECT 
					user_id,
					genre,
					hour,
					listen_count,
					ROW_NUMBER() OVER (
						PARTITION BY user_id, hour
						ORDER BY listen_count DESC
					) AS rank
				FROM {final_aggregate}
			),
			top_genres AS (
				SELECT user_id, genre, hour, listen_count
				FROM ranked_genres
				WHERE rank <= 10
			),
			all_genre_time_combinations AS (
				SELECT DISTINCT 
					tg.user_id, 
					tg.hour, 
					tg.genre
				FROM top_genres tg
			)
			SELECT 
				agtc.user_id,
				sort_array(
					collect_list(
						struct(
							agtc.genre,
							agtc.hour,
							COALESCE(tg.listen_count, 0) AS listen_count
						)
					)
				) AS genre_activity
			FROM all_genre_time_combinations agtc
			LEFT JOIN top_genres tg
				ON agtc.user_id = tg.user_id
			AND agtc.genre = tg.genre
			AND agtc.hour = tg.hour
			GROUP BY agtc.user_id
		"""
		
class GenreActivityUserMessageCreator(UserStatsMessageCreator):

    def __init__(self, message_type: str, selector: StatsRangeListenRangeSelector, database=None):
        super().__init__("genre_activity", message_type, selector, database)

    @property
    def default_database_prefix(self):
        return f"{self.entity}_{self.stats_range}"

    def parse_row(self, entry: dict):
        try:
            UserStatRecords[GenreActivityRecord](
                user_id=entry["user_id"],
                data=entry["genre_activity"]
            )
            return {
                "user_id": entry["user_id"],
                "data": entry["genre_activity"]
            }
        except ValidationError:
            logger.error("Invalid entry in genre trend stats:", exc_info=True)