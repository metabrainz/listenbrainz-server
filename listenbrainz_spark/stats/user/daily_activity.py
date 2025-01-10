import logging
from typing import Iterator, Optional, Dict

from listenbrainz_spark.stats.incremental.user.daily_activity import DailyActivityUserEntity


logger = logging.getLogger(__name__)


def get_daily_activity(stats_range: str, database: str = None) -> Iterator[Optional[Dict]]:
    """ Calculate number of listens for an user for the specified time range """
    logger.debug(f"Calculating daily_activity_{stats_range}")
    entity_obj = DailyActivityUserEntity(stats_range, database, "user_daily_activity")
    return entity_obj.main(0)
