import logging
from typing import Iterator, Optional, Dict

from listenbrainz_spark.stats.incremental.incremental_stats_engine import IncrementalStatsEngine
from listenbrainz_spark.stats.incremental.range_selector import StatsRangeListenRangeSelector
from listenbrainz_spark.stats.incremental.sitewide.era_activity import EraActivitySitewideStatsQuery, \
    EraActivitySitewideMessageCreator

logger = logging.getLogger(__name__)


def get_era_activity(stats_range: str) -> Iterator[Optional[Dict]]:
    """ Calculate number of listens by release year for the specified time range """
    logger.debug(f"Calculating era_activity_{stats_range}")
    selector = StatsRangeListenRangeSelector(stats_range)
    entity_obj = EraActivitySitewideStatsQuery(selector)
    message_creator = EraActivitySitewideMessageCreator(selector)
    engine = IncrementalStatsEngine(entity_obj, message_creator)
    return engine.run()