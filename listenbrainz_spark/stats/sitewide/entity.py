import logging
from typing import Dict, Iterator, Type

from listenbrainz_spark.stats import SITEWIDE_STATS_ENTITY_LIMIT, run_query
from listenbrainz_spark.stats.incremental.incremental_stats_engine import IncrementalStatsEngine
from listenbrainz_spark.stats.incremental.range_selector import StatsRangeListenRangeSelector
from listenbrainz_spark.stats.incremental.sitewide.artist import AritstSitewideEntity
from listenbrainz_spark.stats.incremental.sitewide.artist_map import ArtistMapSitewideEntity, \
    ArtistMapSitewideStatsMessageCreator
from listenbrainz_spark.stats.incremental.sitewide.entity import SitewideEntityStatsQueryProvider, \
    SitewideEntityStatsMessageCreator
from listenbrainz_spark.stats.incremental.sitewide.recording import RecordingSitewideEntity
from listenbrainz_spark.stats.incremental.sitewide.release import ReleaseSitewideEntity
from listenbrainz_spark.stats.incremental.sitewide.release_group import ReleaseGroupSitewideEntity

logger = logging.getLogger(__name__)

incremental_sitewide_map: Dict[str, Type[SitewideEntityStatsQueryProvider]] = {
    "artists": AritstSitewideEntity,
    "releases": ReleaseSitewideEntity,
    "recordings": RecordingSitewideEntity,
    "release_groups": ReleaseGroupSitewideEntity,
}


def get_entity_stats(entity: str, stats_range: str) -> Iterator[Dict]:
    """ Returns top entity stats for given time period """
    logger.debug(f"Calculating sitewide_{entity}_{stats_range}...")
    selector = StatsRangeListenRangeSelector(stats_range)
    entity_cls = incremental_sitewide_map[entity]
    entity_obj: SitewideEntityStatsQueryProvider = entity_cls(selector, SITEWIDE_STATS_ENTITY_LIMIT)
    message_creator = SitewideEntityStatsMessageCreator(entity, selector)
    engine = IncrementalStatsEngine(entity_obj, message_creator)

    if entity == "artists":
        artist_stats = engine.run()
        for message in artist_stats:
            yield message

        artist_map_entity = ArtistMapSitewideEntity(selector, SITEWIDE_STATS_ENTITY_LIMIT)
        artist_map_message_creator = ArtistMapSitewideStatsMessageCreator(selector)
        artist_map_query = artist_map_entity.get_stats_query(engine._final_table, engine._cache_tables)
        artist_map_results = run_query(artist_map_query)
        artist_map_stats = engine.create_messages(artist_map_results, engine._only_inc, artist_map_message_creator)
        for message in artist_map_stats:
            yield message
    else:
        return engine.run()
