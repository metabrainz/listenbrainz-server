from datetime import datetime, date, time

from listenbrainz_spark.stats.incremental.user.artist import ArtistUserEntity
from listenbrainz_spark.stats.incremental.user.recording import RecordingUserEntity
from listenbrainz_spark.stats.incremental.user.release_group import ReleaseGroupUserEntity

NUMBER_OF_YIM_ENTITIES = 50


def calculate_top_entity_stats(year):
    from_date = datetime(year, 1, 1)
    to_date = datetime.combine(date(year, 12, 31), time.max)

    for entity_cls in [ArtistUserEntity, RecordingUserEntity, ReleaseGroupUserEntity]:
        entity_obj = entity_cls(
            stats_range=None, database=None, from_date=from_date, to_date=to_date,
            message_type="year_in_music_top_stats"
        )
        for message in entity_obj.main(50):
            # yim stats are stored in postgres instead of couchdb so drop those messages for yim
            if message["type"] == "couchdb_data_start" or message["type"] == "couchdb_data_end":
                continue

            message["year"] = year
            yield message
