import logging
from typing import Iterator, Optional, Dict, Type

from pandas import DataFrame

from listenbrainz_spark.stats import run_query
from listenbrainz_spark.stats.incremental.incremental_stats_engine import IncrementalStatsEngine
from listenbrainz_spark.stats.incremental.range_selector import StatsRangeListenRangeSelector
from listenbrainz_spark.stats.incremental.user.artist import ArtistUserEntity
from listenbrainz_spark.stats.incremental.user.artist_map import ArtistMapUserEntity, ArtistMapStatsMessageCreator
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
}

NUMBER_OF_TOP_ENTITIES = 1000  # number of top entities to retain for user stats


def get_entity_stats(entity: str, stats_range: str, database: str = None) -> Iterator[Optional[Dict]]:
    """ Get the top entity for all users for specified stats_range """
    logger.debug(f"Calculating user_{entity}_{stats_range}...")
    selector = StatsRangeListenRangeSelector(stats_range)
    entity_obj = incremental_entity_map[entity](selector, NUMBER_OF_TOP_ENTITIES)
    message_creator = UserEntityStatsMessageCreator(entity, "user_entity", selector, database)
    engine = IncrementalStatsEngine(entity_obj, message_creator)
    if entity == "artists":
        artist_stats = engine.run()
        for message in artist_stats:
            yield message

        artist_map_database = database.replace("artists", "artist_map") if database else None
        artist_map_entity = ArtistMapUserEntity(selector, NUMBER_OF_TOP_ENTITIES)
        artist_map_message_creator = ArtistMapStatsMessageCreator(entity, "user_entity", selector, artist_map_database)
        artist_map_query = artist_map_entity.get_stats_query(engine._final_table, engine._cache_tables)
        artist_map_results = run_query(artist_map_query)
        artist_map_stats = engine.create_messages(artist_map_results, engine._only_inc, artist_map_message_creator)

        for message in artist_map_stats:
            yield message
    else:
        return engine.run()
