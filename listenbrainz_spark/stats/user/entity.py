import json
import logging
from datetime import datetime, date
from typing import Iterator, Optional, Dict

from more_itertools import chunked
from pydantic import ValidationError

from data.model.user_artist_stat import ArtistRecord
from data.model.user_recording_stat import RecordingRecord
from data.model.user_release_group_stat import ReleaseGroupRecord
from data.model.user_release_stat import ReleaseRecord
from listenbrainz_spark.path import RELEASE_METADATA_CACHE_DATAFRAME, ARTIST_COUNTRY_CODE_DATAFRAME, \
    RELEASE_GROUP_METADATA_CACHE_DATAFRAME, RECORDING_ARTIST_DATAFRAME
from listenbrainz_spark.stats.incremental.user.artist import ArtistUserEntity
from listenbrainz_spark.stats.incremental.user.recording import RecordingUserEntity
from listenbrainz_spark.stats.incremental.user.release import ReleaseUserEntity
from listenbrainz_spark.stats.incremental.user.release_group import ReleaseGroupUserEntity
from listenbrainz_spark.stats.user import USERS_PER_MESSAGE
from listenbrainz_spark.stats.user.artist import get_artists
from listenbrainz_spark.stats.user.recording import get_recordings
from listenbrainz_spark.stats.user.release import get_releases
from listenbrainz_spark.stats.user.release_group import get_release_groups

logger = logging.getLogger(__name__)

entity_handler_map = {
    "artists": get_artists,
    "releases": get_releases,
    "recordings": get_recordings,
    "release_groups": get_release_groups,
}

entity_model_map = {
    "artists": ArtistRecord,
    "releases": ReleaseRecord,
    "recordings": RecordingRecord,
    "release_groups": ReleaseGroupRecord,
}

entity_cache_map = {
    "artists": [ARTIST_COUNTRY_CODE_DATAFRAME],
    "releases": [RELEASE_METADATA_CACHE_DATAFRAME],
    "recordings": [RECORDING_ARTIST_DATAFRAME, RELEASE_METADATA_CACHE_DATAFRAME],
    "release_groups": [RELEASE_METADATA_CACHE_DATAFRAME, RELEASE_GROUP_METADATA_CACHE_DATAFRAME]
}

incremental_entity_map = {
    "artists": ArtistUserEntity,
    "releases": ReleaseUserEntity,
    "recordings": RecordingUserEntity,
    "release_groups": ReleaseGroupUserEntity,
}

NUMBER_OF_TOP_ENTITIES = 1000  # number of top entities to retain for user stats
NUMBER_OF_YIM_ENTITIES = 50  # number of top entities to retain for Year in Music stats


def get_entity_stats(entity: str, stats_range: str, message_type: str = "user_entity", database: str = None)\
        -> Iterator[Optional[Dict]]:
    """ Get the top entity for all users for specified stats_range """
    logger.debug(f"Calculating user_{entity}_{stats_range}...")

    if message_type == "year_in_music_top_stats":
        number_of_results = NUMBER_OF_YIM_ENTITIES
    else:
        number_of_results = NUMBER_OF_TOP_ENTITIES

    entity_cls = incremental_entity_map[entity]
    entity_obj = entity_cls(stats_range)
    from_date, to_date, only_inc_users, data = entity_obj.generate_stats(number_of_results)
    return create_messages(only_inc_users, data=data, entity=entity, stats_range=stats_range, from_date=from_date,
                           to_date=to_date, message_type=message_type, database=database)


def parse_one_user_stats(entry, entity: str, stats_range: str):
    _dict = entry.asDict(recursive=True)
    count_key = entity + "_count"
    total_entity_count = _dict[count_key]

    entity_list = []
    for item in _dict[entity]:
        try:
            entity_model_map[entity](**item)
            entity_list.append(item)
        except ValidationError:
            logger.error("Invalid entry in entity stats", exc_info=True)
            total_entity_count -= 1

    try:
        return {
            "user_id": _dict["user_id"],
            "data": entity_list,
            "count": total_entity_count
        }
    except ValidationError:
        logger.error(f"""ValidationError while calculating {stats_range} top {entity} for user: 
        {_dict["user_id"]}. Data: {json.dumps(_dict, indent=3)}""", exc_info=True)
        return None


def create_messages(only_inc_users, data, entity: str, stats_range: str, from_date: datetime, to_date: datetime,
                    message_type: str, database: str = None) \
        -> Iterator[Optional[Dict]]:
    """
    Create messages to send the data to the webserver via RabbitMQ

    Args:
        only_inc_users: whether stats were generated only for users with listens present in incremental dumps
        data: Data to sent to the webserver
        entity: The entity for which statistics are calculated, i.e 'artists',
            'releases' or 'recordings'
        stats_range: The range for which the statistics have been calculated
        from_date: The start time of the stats
        to_date: The end time of the stats
        message_type: used to decide which handler on LB webserver side should
            handle this message. can be "user_entity" or "year_in_music_top_stats"
        database: the name of the database in which the webserver should store the data

    Returns:
        messages: A list of messages to be sent via RabbitMQ
    """
    if database is None:
        database = f"{entity}_{stats_range}_{date.today().strftime('%Y%m%d')}"

    if not only_inc_users:
        yield {
            "type": "couchdb_data_start",
            "database": database
        }

    from_ts = int(from_date.timestamp())
    to_ts = int(to_date.timestamp())

    for entries in chunked(data, USERS_PER_MESSAGE):
        multiple_user_stats = []
        for entry in entries:
            processed_stat = parse_one_user_stats(entry, entity, stats_range)
            multiple_user_stats.append(processed_stat)

        yield {
            "type": message_type,
            "stats_range": stats_range,
            "from_ts": from_ts,
            "to_ts": to_ts,
            "entity": entity,
            "data": multiple_user_stats,
            "database": database
        }

    if not only_inc_users:
        yield {
            "type": "couchdb_data_end",
            "database": database
        }
