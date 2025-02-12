import logging
from typing import Iterator, Optional, Dict, Type

from pandas import DataFrame

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


class ArtistMapIncrementalStatsEngine(IncrementalStatsEngine):
    """ Stats engine with disk writes stubbed out because we only want to read from the aggregates from the disk
    and not write new ones
    """

    def create_partial_aggregate(self) -> DataFrame:
        pass

    def bookkeep_incremental_aggregate(self):
        pass


def get_entity_stats(entity: str, stats_range: str, database: str = None) -> Iterator[Optional[Dict]]:
    """ Get the top entity for all users for specified stats_range """
    logger.debug(f"Calculating user_{entity}_{stats_range}...")
    selector = StatsRangeListenRangeSelector(stats_range)
    entity_obj = incremental_entity_map[entity](selector, NUMBER_OF_TOP_ENTITIES)
    if entity == "artist_map":
        message_cls = ArtistMapStatsMessageCreator
        engine_cls = ArtistMapIncrementalStatsEngine
    else:
        message_cls = UserEntityStatsMessageCreator
        engine_cls = IncrementalStatsEngine
    message_creator = message_cls(entity, "user_entity", selector, database)
    engine = engine_cls(entity_obj, message_creator)
    return engine.run()
