import logging
from typing import Iterator, Optional, Dict

from listenbrainz_spark.stats.incremental.incremental_stats_engine import IncrementalStatsEngine
from listenbrainz_spark.stats.incremental.range_selector import StatsRangeListenRangeSelector
from listenbrainz_spark.stats.incremental.user.artist_evolution import (
    ArtistEvolutionUserStatsQueryEntity,
    ArtistEvolutionUserMessageCreator,
)

logger = logging.getLogger(__name__)


def get_artist_evolution_activity(stats_range: str, database: str = None) -> Iterator[Optional[Dict]]:
    """ Calculate user artist evolution activity for the specified time range """
    logger.debug(f"Calculating artist_evolution_{stats_range}")
    selector = StatsRangeListenRangeSelector(stats_range)
    entity_obj = ArtistEvolutionUserStatsQueryEntity(selector)
    message_creator = ArtistEvolutionUserMessageCreator("user_artist_evolution", selector, database)
    engine = IncrementalStatsEngine(entity_obj, message_creator)
    return engine.run()
