from listenbrainz_spark.stats.incremental.aggregator import Aggregator
from listenbrainz_spark.stats.incremental.range_selector import ListeningActivityListenRangeSelector
from listenbrainz_spark.stats.incremental.user.listening_activity import ListeningActivityUserEntity, \
    ListeningActivityUserMessageCreator


def calculate_listens_per_day(year):
    selector = ListeningActivityListenRangeSelector("year_in_music", year)
    entity_obj = ListeningActivityUserEntity(selector)
    message_creator = ListeningActivityUserMessageCreator("year_in_music_listens_per_day", selector)
    aggregator = Aggregator(entity_obj, message_creator)
    for message in aggregator.main():
        # yim stats are stored in postgres instead of couchdb so drop those messages for yim
        if message["type"] == "couchdb_data_start" or message["type"] == "couchdb_data_end":
            continue

        message["year"] = year
        yield message
