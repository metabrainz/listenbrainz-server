import json
import logging
from datetime import datetime
from typing import Iterator, Optional, Dict

from more_itertools import chunked
from pydantic import ValidationError

from data.model.user_artist_stat import ArtistRecord
from data.model.user_entity import UserEntityStatMessage, UserEntityRecords
from data.model.user_recording_stat import RecordingRecord
from data.model.user_release_stat import ReleaseRecord
from listenbrainz_spark.stats import get_dates_for_stats_range
from listenbrainz_spark.stats.user import USERS_PER_MESSAGE
from listenbrainz_spark.stats.user.artist import get_artists
from listenbrainz_spark.stats.user.recording import get_recordings
from listenbrainz_spark.stats.user.release import get_releases
from listenbrainz_spark.utils import get_listens_from_new_dump

logger = logging.getLogger(__name__)

entity_handler_map = {
    "artists": get_artists,
    "releases": get_releases,
    "recordings": get_recordings
}

entity_model_map = {
    "artists": ArtistRecord,
    "releases": ReleaseRecord,
    "recordings": RecordingRecord
}


def get_entity_stats(entity: str, stats_range: str, message_type="user_entity")\
        -> Iterator[Optional[Dict]]:
    """ Get the top entity for all users for specified stats_range """
    logger.debug(f"Calculating user_{entity}_{stats_range}...")

    from_date, to_date = get_dates_for_stats_range(stats_range)
    listens_df = get_listens_from_new_dump(from_date, to_date)
    table = f"user_{entity}_{stats_range}"
    listens_df.createOrReplaceTempView(table)

    messages = calculate_entity_stats(
        from_date, to_date, table, entity, stats_range, message_type
    )

    logger.debug("Done!")

    return messages


def calculate_entity_stats(from_date: datetime, to_date: datetime, table: str,
                           entity: str, stats_range: str, message_type: str):
    handler = entity_handler_map[entity]
    data = handler(table)
    return create_messages(data=data, entity=entity, stats_range=stats_range,
                           from_date=from_date, to_date=to_date, message_type=message_type)


def parse_one_user_stats(entry, entity: str, stats_range: str, message_type: str) \
        -> Optional[UserEntityRecords]:
    _dict = entry.asDict(recursive=True)
    total_entity_count = len(_dict[entity])

    if message_type == "year_in_music_top_stats":
        # for year in music, only retain top 50 stats
        retain = 50
    else:
        # otherwise retain top 1000 stats
        retain = 1000

    entity_list = []
    for item in _dict[entity][:retain]:
        try:
            entity_list.append(entity_model_map[entity](**item))
        except ValidationError:
            logger.error("Invalid entry in entity stats", exc_info=True)

    try:
        return UserEntityRecords(
            user_id=_dict["user_id"],
            data=entity_list,
            count=total_entity_count
        )
    except ValidationError:
        logger.error(f"""ValidationError while calculating {stats_range} top {entity} for user: 
        {_dict["user_id"]}. Data: {json.dumps(_dict, indent=3)}""", exc_info=True)
        return None


def create_messages(data, entity: str, stats_range: str, from_date: datetime, to_date: datetime,
                    message_type) \
        -> Iterator[Optional[Dict]]:
    """
    Create messages to send the data to the webserver via RabbitMQ

    Args:
        data: Data to sent to the webserver
        entity: The entity for which statistics are calculated, i.e 'artists',
            'releases' or 'recordings'
        stats_range: The range for which the statistics have been calculated
        from_date: The start time of the stats
        to_date: The end time of the stats
        message_type: used to decide which handler on LB webserver side should
            handle this message. can be "user_entity" or "year_in_music_top_stats"

    Returns:
        messages: A list of messages to be sent via RabbitMQ
    """
    from_ts = int(from_date.timestamp())
    to_ts = int(to_date.timestamp())

    for entries in chunked(data, USERS_PER_MESSAGE):
        multiple_user_stats = []
        for entry in entries:
            processed_stat = parse_one_user_stats(entry, entity, stats_range, message_type)
            multiple_user_stats.append(processed_stat)

        try:
            model = UserEntityStatMessage(**{
                "type": message_type,
                "stats_range": stats_range,
                "from_ts": from_ts,
                "to_ts": to_ts,
                "entity": entity,
                "data": multiple_user_stats,
            })
            result = model.dict(exclude_none=True)
            yield result
        except ValidationError:
            logger.error(f"""ValidationError while calculating {stats_range} top {entity}:""", exc_info=True)
            yield None
