import logging
from typing import Iterator, Optional, Dict

from listenbrainz_spark.stats.incremental.incremental_stats_engine import IncrementalStatsEngine
from listenbrainz_spark.stats.incremental.range_selector import StatsRangeListenRangeSelector
from listenbrainz_spark.stats.incremental.user.genre_activity import GenreActivityUserStatsQueryEntity, \
	GenreActivityUserMessageCreator

logger = logging.getLogger(__name__)


def get_genre_activity(stats_range: str, database: str = None) -> Iterator[Optional[Dict]]:
	""" Calculate number of listens per genre for an user grouped by time of the day for the specified time range """
	logger.debug(f"Calculating genre_activity_{stats_range}")
	selector = StatsRangeListenRangeSelector(stats_range)
	entity_obj = GenreActivityUserStatsQueryEntity(selector)
	message_creator = GenreActivityUserMessageCreator("user_genre_activity", selector, database)
	engine = IncrementalStatsEngine(entity_obj, message_creator)
	return engine.run()