import logging
from typing import Iterator, Optional, Dict, Type

from listenbrainz_spark.stats.incremental.incremental_stats_engine import IncrementalStatsEngine
from listenbrainz_spark.stats.incremental.listener.artist import ArtistEntityListenerStatsQuery
from listenbrainz_spark.stats.incremental.listener.entity import EntityListenerStatsQueryProvider, EntityListenerStatsMessageCreator
from listenbrainz_spark.stats.incremental.listener.release_group import ReleaseGroupEntityListenerStatsQuery
from listenbrainz_spark.stats.incremental.range_selector import StatsRangeListenRangeSelector

logger = logging.getLogger(__name__)

incremental_entity_obj_map: Dict[str, Type[EntityListenerStatsQueryProvider]] = {
    "artists": ArtistEntityListenerStatsQuery,
    "release_groups": ReleaseGroupEntityListenerStatsQuery,
}

NUMBER_OF_TOP_LISTENERS = 10  # number of top listeners to retain for user stats


def get_listener_stats(entity: str, stats_range: str, database: str = None) -> Iterator[Optional[Dict]]:
    """ Get the top listeners for all entity for specified stats_range """
    logger.debug(f"Calculating {entity}_listeners_{stats_range}...")
    selector = StatsRangeListenRangeSelector(stats_range)
    entity_cls = incremental_entity_obj_map[entity]
    entity_obj = entity_cls(selector, NUMBER_OF_TOP_LISTENERS)
    message_creator = EntityListenerStatsMessageCreator(entity, "entity_listener", selector, database)
    engine = IncrementalStatsEngine(entity_obj, message_creator)
    return engine.run()
