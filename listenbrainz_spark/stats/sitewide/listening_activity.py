import logging
from typing import Iterator, Optional, Dict

from listenbrainz_spark.stats.incremental.incremental_stats_engine import IncrementalStatsEngine
from listenbrainz_spark.stats.incremental.range_selector import ListeningActivityListenRangeSelector
from listenbrainz_spark.stats.incremental.sitewide.listening_activity import ListeningActivitySitewideStatsQuery, \
    ListeningActivitySitewideMessageCreator

logger = logging.getLogger(__name__)


def get_listening_activity(stats_range: str) -> Iterator[Optional[Dict]]:
    """ Compute the number of listens for a time range compared to the previous range

    Given a time range, this computes a histogram of all listens for that range
    and the previous range of the same duration, so that they can be compared. The
    bin size of the histogram depends on the size of the range (e.g.
    year -> 12 months, month -> ~30 days, week -> ~7 days, see get_time_range for
    details). These values are used on the listening activity reports.
    """
    logger.debug(f"Calculating listening_activity_{stats_range}")
    selector = ListeningActivityListenRangeSelector(stats_range)
    entity_obj = ListeningActivitySitewideStatsQuery(selector)
    message_creator = ListeningActivitySitewideMessageCreator(selector)
    engine = IncrementalStatsEngine(entity_obj, message_creator)
    return engine.run()
