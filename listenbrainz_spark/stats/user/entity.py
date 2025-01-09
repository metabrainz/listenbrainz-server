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
NUMBER_OF_YIM_ENTITIES = 50  # number of top entities to retain for Year in Music stats


def get_entity_stats(entity: str, stats_range: str, message_type: str = "user_entity", database: str = None) \
        -> Iterator[Optional[Dict]]:
    """ Get the top entity for all users for specified stats_range """
    logger.debug(f"Calculating user_{entity}_{stats_range}...")

    if message_type == "year_in_music_top_stats":
        number_of_results = NUMBER_OF_YIM_ENTITIES
    else:
        number_of_results = NUMBER_OF_TOP_ENTITIES

    entity_cls = incremental_entity_map[entity]
    entity_obj = entity_cls(stats_range, database, message_type)
    return entity_obj.main(number_of_results)
