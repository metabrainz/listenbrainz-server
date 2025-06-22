import logging
from typing import Iterator, Optional, Dict

from listenbrainz_spark.stats.incremental.incremental_stats_engine import IncrementalStatsEngine
from listenbrainz_spark.stats.incremental.range_selector import ListenRangeSelector
from listenbrainz_spark.stats.incremental.sitewide.genre_activity import GenreActivitySitewideStatsQuery, \
    GenreActivitySitewideMessageCreator

logger = logging.getLogger(__name__)


def get_genre_activity(stats_range: str) -> Iterator[Optional[Dict]]:
    """ Compute the genre distribution across different time brackets for a given time range

    Given a time range, this computes a histogram of all listens grouped by genre
    and time bracket (00-06, 06-12, 12-18, 18-24) for that range. The genre trend
    shows how different music genres are distributed throughout the day, providing
    insights into listening patterns. These values are used for genre trend reports
    and circular/radial visualizations.
    """
    logger.debug(f"Calculating genre_trend_{stats_range}")
    selector = ListenRangeSelector(stats_range)
    entity_obj = GenreActivitySitewideStatsQuery(selector)
    message_creator = GenreActivitySitewideMessageCreator(selector)
    engine = IncrementalStatsEngine(entity_obj, message_creator)
    return engine.run()