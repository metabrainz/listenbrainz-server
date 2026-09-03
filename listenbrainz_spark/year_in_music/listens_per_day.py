from listenbrainz_spark.stats.incremental.range_selector import ListeningActivityListenRangeSelector
from listenbrainz_spark.stats.incremental.user.listening_activity import ListeningActivityUserStatsQueryEntity, \
    ListeningActivityUserMessageCreator
from listenbrainz_spark.year_in_music.stats_engine import YIMStatsEngine


def calculate_listens_per_day(year):
    selector = ListeningActivityListenRangeSelector("year_in_music", year)
    entity_obj = ListeningActivityUserStatsQueryEntity(selector)
    message_creator = ListeningActivityUserMessageCreator("year_in_music_listens_per_day", selector)
    engine = YIMStatsEngine(entity_obj, message_creator)
    for message in engine.run():
        message["year"] = year
        yield message
