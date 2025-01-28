import logging
from typing import Iterator, Optional, Dict

from listenbrainz_spark.stats.incremental.incremental_stats_engine import IncrementalStatsEngine
from listenbrainz_spark.stats.incremental.range_selector import StatsRangeListenRangeSelector
from listenbrainz_spark.stats.incremental.user.daily_activity import DailyActivityUserStatsQueryEntity, \
    DailyActivityUserMessageCreator

logger = logging.getLogger(__name__)


def get_daily_activity(stats_range: str, database: str = None) -> Iterator[Optional[Dict]]:
    """ Calculate number of listens for an user for the specified time range """
    logger.debug(f"Calculating daily_activity_{stats_range}")
    selector = StatsRangeListenRangeSelector(stats_range)
    entity_obj = DailyActivityUserStatsQueryEntity(selector)
    message_creator = DailyActivityUserMessageCreator("user_daily_activity", selector, database)
    engine = IncrementalStatsEngine(entity_obj, message_creator)
    return engine.run()
