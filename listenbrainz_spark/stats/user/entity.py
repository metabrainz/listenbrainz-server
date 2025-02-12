import logging
from typing import Iterator, Optional, Dict, Type

from listenbrainz_spark.stats.incremental.incremental_stats_engine import IncrementalStatsEngine
from listenbrainz_spark.stats.incremental.range_selector import StatsRangeListenRangeSelector
from listenbrainz_spark.stats.incremental.user.artist import ArtistUserEntity
from listenbrainz_spark.stats.incremental.user.artist_map import ArtistMapUserEntity
from listenbrainz_spark.stats.incremental.user.entity import UserEntityStatsQueryProvider, \
    UserEntityStatsMessageCreator
from listenbrainz_spark.stats.incremental.user.recording import RecordingUserEntity
from listenbrainz_spark.stats.incremental.user.release import ReleaseUserEntity
from listenbrainz_spark.stats.incremental.user.release_group import ReleaseGroupUserEntity

logger = logging.getLogger(__name__)

incremental_entity_map: Dict[str, Type[UserEntityStatsQueryProvider]] = {
    "artists": ArtistUserEntity,
    "releases": ReleaseUserEntity,
    "recordings": RecordingUserEntity,
    "release_groups": ReleaseGroupUserEntity,
    "artist_map": ArtistMapUserEntity,
}

NUMBER_OF_TOP_ENTITIES = 1000  # number of top entities to retain for user stats


class ArtistMapStatsMessageCreator(UserEntityStatsMessageCreator):

    def parse_row(self, row):
        return row


def get_entity_stats(entity: str, stats_range: str, database: str = None) -> Iterator[Optional[Dict]]:
    """ Get the top entity for all users for specified stats_range """
    logger.debug(f"Calculating user_{entity}_{stats_range}...")
    selector = StatsRangeListenRangeSelector(stats_range)
    entity_obj = incremental_entity_map[entity](selector, NUMBER_OF_TOP_ENTITIES)
    if entity == "artist_map":
        entity_cls = ArtistMapStatsMessageCreator
    else:
        entity_cls = UserEntityStatsMessageCreator
    message_creator = entity_cls(entity, "user_entity", selector, database)
    engine = IncrementalStatsEngine(entity_obj, message_creator)
    return engine.run()
