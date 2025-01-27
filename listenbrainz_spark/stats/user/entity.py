import logging
from typing import Iterator, Optional, Dict

from listenbrainz_spark.stats.incremental.user.artist import ArtistUserEntity
from listenbrainz_spark.stats.incremental.user.recording import RecordingUserEntity
from listenbrainz_spark.stats.incremental.user.release import ReleaseUserEntity
from listenbrainz_spark.stats.incremental.user.release_group import ReleaseGroupUserEntity

logger = logging.getLogger(__name__)

incremental_entity_map = {
    "artists": ArtistUserEntity,
    "releases": ReleaseUserEntity,
    "recordings": RecordingUserEntity,
    "release_groups": ReleaseGroupUserEntity,
}

NUMBER_OF_TOP_ENTITIES = 1000  # number of top entities to retain for user stats


def get_entity_stats(entity: str, stats_range: str, database: str = None) -> Iterator[Optional[Dict]]:
    """ Get the top entity for all users for specified stats_range """
    logger.debug(f"Calculating user_{entity}_{stats_range}...")
    entity_cls = incremental_entity_map[entity]
    entity_obj = entity_cls(stats_range, database, "user_entity")
    return entity_obj.main(NUMBER_OF_TOP_ENTITIES)
