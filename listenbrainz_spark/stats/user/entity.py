import json
import logging
from datetime import datetime
from typing import Iterator, Optional

from pydantic import ValidationError

from data.model.user_entity import UserEntityStatMessage
from data.model.user_artist_stat import UserArtistRecord
from data.model.user_release_stat import UserReleaseRecord
from data.model.user_recording_stat import UserRecordingRecord
from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.stats import offset_days, replace_days, replace_months, get_last_monday
from listenbrainz_spark.stats.user.artist import get_artists
from listenbrainz_spark.stats.user.recording import get_recordings
from listenbrainz_spark.stats.user.release import get_releases
from listenbrainz_spark.utils import get_listens_from_new_dump, get_latest_listen_ts

logger = logging.getLogger(__name__)

entity_handler_map = {
    "artists": get_artists,
    "releases": get_releases,
    "recordings": get_recordings
}

entity_model_map = {
    "artists": UserArtistRecord,
    "releases": UserReleaseRecord,
    "recordings": UserRecordingRecord
}


def get_entity_week(entity: str) -> Iterator[Optional[UserEntityStatMessage]]:
    """ Get the weekly top entity for all users """
    to_date = get_last_monday(get_latest_listen_ts())
    from_date = offset_days(to_date, 7)
    # Set time to 00:00
    from_date = datetime(from_date.year, from_date.month, from_date.day)
    return _get_entity_stats(entity, "week", from_date, to_date)


def get_entity_month(entity: str) -> Iterator[Optional[UserEntityStatMessage]]:
    """ Get the month top entity for all users """
    to_date = get_latest_listen_ts()
    from_date = replace_days(to_date, 1)
    # Set time to 00:00
    from_date = datetime(from_date.year, from_date.month, from_date.day)
    return _get_entity_stats(entity, "month", from_date, to_date)


def get_entity_year(entity: str) -> Iterator[Optional[UserEntityStatMessage]]:
    """ Get the year top entity for all users """
    to_date = get_latest_listen_ts()
    from_date = replace_days(replace_months(to_date, 1), 1)
    # Set time to 00:00
    from_date = datetime(from_date.year, from_date.month, from_date.day)
    return _get_entity_stats(entity, "year", from_date, to_date)


def get_entity_all_time(entity: str) -> Iterator[Optional[UserEntityStatMessage]]:
    """ Get the all_time top entity for all users """
    to_date = get_latest_listen_ts()
    from_date = datetime(LAST_FM_FOUNDING_YEAR, 1, 1)
    return _get_entity_stats(entity, "all_time", from_date, to_date)


def _get_entity_stats(entity: str, stats_range: str, from_date: datetime, to_date: datetime) \
        -> Iterator[Optional[UserEntityStatMessage]]:
    listens_df = get_listens_from_new_dump(from_date, to_date)
    table_name = f"user_{entity}_{stats_range}"
    listens_df.createOrReplaceTempView(table_name)

    handler = entity_handler_map[entity]
    data = handler(table_name)
    messages = create_messages(data=data, entity=entity, stats_range=stats_range,
                               from_date=from_date, to_date=to_date)

    logger.debug("Done!")

    return messages


def create_messages(data, entity: str, stats_range: str, from_date: datetime, to_date: datetime) \
        -> Iterator[Optional[UserEntityStatMessage]]:
    """
    Create messages to send the data to the webserver via RabbitMQ

    Args:
        data: Data to sent to the webserver
        entity: The entity for which statistics are calculated, i.e 'artists',
            'releases' or 'recordings'
        stats_range: The range for which the statistics have been calculated
        from_date: The start time of the stats
        to_date: The end time of the stats

    Returns:
        messages: A list of messages to be sent via RabbitMQ
    """
    from_ts = int(from_date.timestamp())
    to_ts = int(to_date.timestamp())

    for entry in data:
        _dict = entry.asDict(recursive=True)
        total_entity_count = len(_dict[entity])

        # Clip the recordings to top 1000 so that we don't drop messages
        if entity == "recordings" and stats_range == "all_time":
            _dict[entity] = _dict[entity][:1000]

        entity_list = []
        for item in _dict[entity]:
            try:
                entity_list.append(entity_model_map[entity](**item))
            except ValidationError:
                logger.error("Invalid entry in entity stats", exc_info=True)
        try:
            model = UserEntityStatMessage(**{
                "musicbrainz_id": _dict["user_name"],
                "type": "user_entity",
                "stats_range": stats_range,
                "from_ts": from_ts,
                "to_ts": to_ts,
                "data": entity_list,
                "entity": entity,
                "count": total_entity_count
            })
            result = model.dict(exclude_none=True)
            yield result
        except ValidationError:
            logger.error("""ValidationError while calculating {stats_range} top {entity} for user: {user_name}. 
            Data: {data}""".format(stats_range=stats_range, entity=entity, user_name=_dict["user_name"],
                                   data=json.dumps(_dict, indent=3)), exc_info=True)
            yield None
