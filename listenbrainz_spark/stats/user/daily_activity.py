import logging
from typing import Iterator, Optional, Dict

from listenbrainz_spark.stats.incremental.aggregator import Aggregator
from listenbrainz_spark.stats.incremental.range_selector import StatsRangeListenRangeSelector
from listenbrainz_spark.stats.incremental.user.daily_activity import DailyActivityUserEntity, \
    DailyActivityUserMessageCreator

logger = logging.getLogger(__name__)


def get_daily_activity(stats_range: str, database: str = None) -> Iterator[Optional[Dict]]:
    """ Calculate number of listens for an user for the specified time range """
    logger.debug(f"Calculating daily_activity_{stats_range}")
    selector = StatsRangeListenRangeSelector(stats_range)
    entity_obj = DailyActivityUserEntity(selector)
    message_creator = DailyActivityUserMessageCreator("user_daily_activity", selector, database)
    aggregator = Aggregator(entity_obj, message_creator)
    return aggregator.main()
