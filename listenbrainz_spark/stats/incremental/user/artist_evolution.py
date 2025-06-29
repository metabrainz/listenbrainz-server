import logging
from typing import List

from pydantic import ValidationError

import listenbrainz_spark
from data.model.common_stat_spark import UserStatRecords
from data.model.user_artist_evolution import ArtistEvolutionRecord
from listenbrainz_spark.stats.incremental.range_selector import ListenRangeSelector, StatsRangeListenRangeSelector
from listenbrainz_spark.stats.incremental.user.entity import UserStatsQueryProvider, UserStatsMessageCreator

logger = logging.getLogger(__name__)


class ArtistEvolutionUserStatsQueryEntity(UserStatsQueryProvider):
    """Tracks the number of listens per artist per day."""

    def __init__(self, selector: ListenRangeSelector):
        super().__init__(selector)

    @property
    def entity(self):
        return "artist_evolution"

    def get_aggregate_query(self, table):
        return f"""
            WITH exploded_artists AS (
                SELECT
                    user_id,
                    TRIM(artist) AS artist_name,
                    date_format(listened_at, 'yyyy-MM-dd') AS date
                FROM {table}
                LATERAL VIEW explode(split(data->>'artist_name', ',')) AS artist
            )
            SELECT
                user_id,
                date,
                artist_name,
                COUNT(*) AS listen_count
            FROM exploded_artists
            GROUP BY user_id, date, artist_name
        """

    def get_combine_aggregates_query(self, existing_aggregate, incremental_aggregate):
        return f"""
            WITH intermediate_table AS (
                SELECT * FROM {existing_aggregate}
                UNION ALL
                SELECT * FROM {incremental_aggregate}
            )
            SELECT
                user_id,
                date,
                artist_name,
                SUM(listen_count) AS listen_count
            FROM intermediate_table
            GROUP BY user_id, date, artist_name
        """

    def get_stats_query(self, final_aggregate):
        return f"""
            SELECT user_id,
                   sort_array(
                       collect_list(
                           struct(
                               date,
                               artist_name,
                               COALESCE(listen_count, 0) AS listen_count
                           )
                       )
                   ) AS artist_evolution
            FROM {final_aggregate}
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
            logger.error("Invalid entry in artist evolution stats:", exc_info=True)
