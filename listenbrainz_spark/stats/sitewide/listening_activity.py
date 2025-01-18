import logging
from datetime import datetime
from typing import Iterator, Optional, Dict

from listenbrainz_spark.stats.incremental.sitewide.listening_activity import ListeningActivitySitewideEntity

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
    entity_obj = ListeningActivitySitewideEntity(stats_range)
    return entity_obj.main()
