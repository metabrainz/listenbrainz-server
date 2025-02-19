from datetime import datetime, date, time

from listenbrainz_spark.stats import run_query
from listenbrainz_spark.stats.incremental.incremental_stats_engine import IncrementalStatsEngine
from listenbrainz_spark.stats.incremental.range_selector import FromToRangeListenRangeSelector
from listenbrainz_spark.stats.incremental.user.artist_map import ArtistMapUserEntity, ArtistMapStatsMessageCreator
from listenbrainz_spark.stats.incremental.user.entity import UserStatsMessageCreator
from listenbrainz_spark.stats.user.entity import incremental_entity_map

NUMBER_OF_YIM_ENTITIES = 50


class YIMStatsMessageCreator(UserStatsMessageCreator):

    def __init__(self, entity, selector):
        super().__init__(entity, "year_in_music_top_stats", selector)

    @property
    def default_database_prefix(self):
        return f"{self.entity}_year_in_music"


class YIMArtistMapMessageCreator(ArtistMapStatsMessageCreator):

    def __init__(self, selector):
        super().__init__("artist_map", "year_in_music_artist_map", selector)

    @property
    def default_database_prefix(self):
        return "artist_map_year_in_music"


def calculate_top_entity_stats(year):
    from_date = datetime(year, 1, 1)
    to_date = datetime.combine(date(year, 12, 31), time.max)
    selector = FromToRangeListenRangeSelector(from_date, to_date)

    for entity in ["artists", "recordings", "release_groups"]:
        entity_cls = incremental_entity_map[entity]
        entity_obj = entity_cls(selector, NUMBER_OF_YIM_ENTITIES)
        message_creator = YIMStatsMessageCreator(entity, selector)
        engine = IncrementalStatsEngine(entity_obj, message_creator)
        for message in engine.run():
            # yim stats are stored in postgres instead of couchdb so drop those messages for yim
            if message["type"] == "couchdb_data_start" or message["type"] == "couchdb_data_end":
                continue

            message["year"] = year
            yield message

        if entity == "artists":
            artist_map_entity = ArtistMapUserEntity(selector, NUMBER_OF_YIM_ENTITIES)
            artist_map_message_creator = YIMArtistMapMessageCreator(selector)
            artist_map_query = artist_map_entity.get_stats_query(engine._final_table)
            artist_map_results = run_query(artist_map_query)
            for message in engine.create_messages(artist_map_results, engine._only_inc, artist_map_message_creator):
                if message["type"] == "couchdb_data_start" or message["type"] == "couchdb_data_end":
                    continue

                message["year"] = year
                yield message
