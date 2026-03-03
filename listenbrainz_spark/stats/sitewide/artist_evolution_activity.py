import logging
from typing import Iterator, Optional, Dict

from listenbrainz_spark.stats.incremental.incremental_stats_engine import IncrementalStatsEngine
from listenbrainz_spark.stats.incremental.range_selector import StatsRangeListenRangeSelector
from listenbrainz_spark.stats.incremental.sitewide.artist_evolution_activity import ArtistEvolutionActivitySitewideStatsQuery, \
    ArtistEvolutionActivitySitewideMessageCreator

logger = logging.getLogger(__name__)

TOP_N_ARTISTS = 20


def get_artist_evolution_activity(stats_range: str) -> Iterator[Optional[Dict]]:
    """ Calculate number of listens by release year for the specified time range """
    logger.debug(f"Calculating era_activity_{stats_range}")
    selector = StatsRangeListenRangeSelector(stats_range)
    entity_obj = ArtistEvolutionActivitySitewideStatsQuery(selector, TOP_N_ARTISTS)
    message_creator = ArtistEvolutionActivitySitewideMessageCreator(selector)
    engine = IncrementalStatsEngine(entity_obj, message_creator)
    return engine.run()