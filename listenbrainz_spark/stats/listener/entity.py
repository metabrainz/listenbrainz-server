import logging
from typing import Iterator, Optional, Dict

from listenbrainz_spark.stats.incremental.listener.artist import ArtistEntityListener
from listenbrainz_spark.stats.incremental.listener.release_group import ReleaseGroupEntityListener

logger = logging.getLogger(__name__)

incremental_entity_obj_map = {
    "artists": ArtistEntityListener,
    "release_groups": ReleaseGroupEntityListener,
}

NUMBER_OF_TOP_LISTENERS = 10  # number of top listeners to retain for user stats


def get_listener_stats(entity: str, stats_range: str, database: str = None) -> Iterator[Optional[Dict]]:
    """ Get the top listeners for all entity for specified stats_range """
    logger.debug(f"Calculating {entity}_listeners_{stats_range}...")
    entity_cls = incremental_entity_obj_map[entity]
    entity_obj = entity_cls(stats_range, database)
    return entity_obj.main(NUMBER_OF_TOP_LISTENERS)
