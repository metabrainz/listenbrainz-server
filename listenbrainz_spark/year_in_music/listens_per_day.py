from listenbrainz_spark.stats.incremental.user.listening_activity import ListeningActivityUserEntity


def calculate_listens_per_day(year):
    entity_obj = ListeningActivityUserEntity(
        stats_range="year_in_music", database=None, message_type="year_in_music_listens_per_day",
        year=year
    )
    for message in entity_obj.main(0):
        # yim stats are stored in postgres instead of couchdb so drop those messages for yim
        if message["type"] == "couchdb_data_start" or message["type"] == "couchdb_data_end":
            continue

        message["year"] = year
        yield message
