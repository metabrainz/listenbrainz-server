import logging
from typing import List

from pydantic import ValidationError

import listenbrainz_spark
from data.model.common_stat_spark import UserStatRecords
from data.model.user_artist_evolution import ArtistEvolutionRecord
from listenbrainz_spark.stats.incremental.range_selector import ListenRangeSelector, StatsRangeListenRangeSelector
from listenbrainz_spark.stats.incremental.user.entity import UserStatsQueryProvider, UserStatsMessageCreator
from listenbrainz_spark.utils import read_files_from_HDFS
from listenbrainz_spark.path import RECORDING_ARTIST_DATAFRAME

logger = logging.getLogger(__name__)


class ArtistEvolutionUserStatsQueryEntity(UserStatsQueryProvider):
    """ See base class QueryProvider for details. """

    def __init__(self, selector: ListenRangeSelector):
        super().__init__(selector)

    @property
    def entity(self):
        return "artist_evolution"

    def __get_time_bucket_expression(self, range_type):
        """Determine time bucket expression based on range type"""
        if range_type in ['week', 'last_week']:
            return "date_format(l.listened_at, 'EEEE')"
        elif range_type in ['month', 'last_month']:
            return "date_format(l.listened_at, 'd')"
        elif range_type in ['year', 'last_year']:
            return "date_format(l.listened_at, 'MMMM')"
        elif range_type == 'all_time':
            return "year(l.listened_at)"
        else:
            return "date_format(l.listened_at, 'yyyy-MM-dd')"

    def get_aggregate_query(self, table):
        recording_df = read_files_from_HDFS(RECORDING_ARTIST_DATAFRAME)
        recording_df.createOrReplaceTempView("recording_artist")

        # Get range type from selector - access through the listen_range_selector
        range_type = 'week'
        time_bucket_expr = self.__get_time_bucket_expression(range_type)

        return f"""
            SELECT l.user_id,
                   artist_element.artist_mbid,
                   artist_element.artist_credit_name AS artist_name,
                   {time_bucket_expr} AS time_bucket,
                   COUNT(*) AS listen_count
              FROM {table} l
              JOIN recording_artist ra ON l.recording_mbid = ra.recording_mbid
             LATERAL VIEW explode(ra.artists) exploded_table AS artist_element
             WHERE artist_element.artist_mbid IS NOT NULL
               AND artist_element.artist_credit_name IS NOT NULL
          GROUP BY l.user_id, artist_element.artist_mbid, artist_element.artist_credit_name, {time_bucket_expr}
        """

    def get_combine_aggregates_query(self, existing_aggregate, incremental_aggregate):
        return f"""
            SELECT user_id,
                   artist_mbid,
                   artist_name,
                   time_bucket,
                   SUM(listen_count) AS listen_count
              FROM (
                  SELECT user_id, artist_mbid, artist_name, time_bucket, listen_count
                    FROM {existing_aggregate}
                   UNION ALL
                  SELECT user_id, artist_mbid, artist_name, time_bucket, listen_count
                    FROM {incremental_aggregate}
              ) combined
          GROUP BY user_id, artist_mbid, artist_name, time_bucket
        """

    def get_stats_query(self, final_aggregate):
        return f"""
            WITH ranked_artists AS (
                SELECT user_id,
                       artist_mbid,
                       artist_name,
                       time_bucket,
                       listen_count,
                       ROW_NUMBER() OVER (
                           PARTITION BY user_id, time_bucket
                           ORDER BY listen_count DESC
                       ) AS rank
                  FROM {final_aggregate}
            ),
            top_artists AS (
                SELECT user_id,
                       artist_mbid,
                       artist_name,
                       time_bucket AS date,
                       listen_count
                  FROM ranked_artists
                 WHERE rank <= 50
            )
            SELECT user_id,
                   SORT_ARRAY(
                       COLLECT_LIST(
                           STRUCT(date, artist_mbid, artist_name, listen_count)
                       )
                   ) AS artist_evolution
              FROM top_artists
          GROUP BY user_id
        """


class ArtistEvolutionUserMessageCreator(UserStatsMessageCreator):

    def __init__(self, message_type: str, selector: StatsRangeListenRangeSelector, database=None):
        super().__init__("artist_evolution", message_type, selector, database)

    @property
    def default_database_prefix(self):
        return f"{self.entity}_{self.stats_range}"

    def parse_row(self, entry: dict):
        try:
            UserStatRecords[ArtistEvolutionRecord](
                user_id=entry["user_id"],
                data=entry["artist_evolution"]
            )
            return {
                "user_id": entry["user_id"],
                "data": entry["artist_evolution"]
            }
        except ValidationError:
            logger.error("Invalid entry in artist evolution stats for user %s", 
                        entry.get("user_id", "unknown"), exc_info=True)
            return None