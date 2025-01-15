import logging
from typing import Iterator, Optional, Dict

from listenbrainz_spark.stats.incremental.aggregator import Aggregator
from listenbrainz_spark.stats.incremental.listener.artist import ArtistEntityListener
from listenbrainz_spark.stats.incremental.listener.entity import EntityListenerProvider, EntityStatsMessageCreator
from listenbrainz_spark.stats.incremental.listener.release_group import ReleaseGroupEntityListener
from listenbrainz_spark.stats.incremental.range_selector import StatsRangeListenRangeSelector

logger = logging.getLogger(__name__)

incremental_entity_obj_map: Dict[str, type[EntityListenerProvider]] = {
    "artists": ArtistEntityListener,
    "release_groups": ReleaseGroupEntityListener,
}

NUMBER_OF_TOP_LISTENERS = 10  # number of top listeners to retain for user stats


def get_listener_stats(entity: str, stats_range: str, database: str = None) -> Iterator[Optional[Dict]]:
    """ Get the top listeners for all entity for specified stats_range """
    logger.debug(f"Calculating {entity}_listeners_{stats_range}...")
    selector = StatsRangeListenRangeSelector(stats_range)
    entity_cls = incremental_entity_obj_map[entity]
    entity_obj = entity_cls(selector, NUMBER_OF_TOP_LISTENERS)
    message_creator = EntityStatsMessageCreator(entity, "entity_listener", selector, database)
    aggregator = Aggregator(entity_obj, message_creator)
    return aggregator.main()
