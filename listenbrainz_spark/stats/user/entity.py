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
from listenbrainz_spark.path import LISTENBRAINZ_DATA_DIRECTORY
from listenbrainz_spark.stats import (offset_days, replace_days,
                                      replace_months, run_query)
from listenbrainz_spark.stats.user.artist import get_artists
from listenbrainz_spark.stats.user.recording import get_recordings
from listenbrainz_spark.stats.user.release import get_releases
from listenbrainz_spark.stats.utils import (filter_listens,
                                            get_last_monday,
                                            get_latest_listen_ts)
from listenbrainz_spark.utils import get_listens


logger = logging.getLogger(__name__)

entity_handler_map = {
    'artists': get_artists,
    'releases': get_releases,
    'recordings': get_recordings
}

entity_model_map = {
    'artists': UserArtistRecord,
    'releases': UserReleaseRecord,
    'recordings': UserRecordingRecord
}


def get_entity_week(entity: str) -> Iterator[Optional[UserEntityStatMessage]]:
    """ Get the weekly top entity for all users """
    logger.debug("Calculating {}_week...".format(entity))

    date = get_latest_listen_ts()

    to_date = get_last_monday(date)
    from_date = offset_days(to_date, 7)

    listens_df = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
    filtered_df = filter_listens(listens_df, from_date, to_date)
    table_name = 'user_{}_week'.format(entity)
    filtered_df.createOrReplaceTempView(table_name)

    handler = entity_handler_map[entity]
    data = handler(table_name)
    messages = create_messages(data=data, entity=entity, stats_range='week',
                               from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    logger.debug("Done!")

    return messages


def get_entity_month(entity: str) -> Iterator[Optional[UserEntityStatMessage]]:
    """ Get the month top entity for all users """
    logger.debug("Calculating {}_month...".format(entity))

    to_date = get_latest_listen_ts()
    from_date = replace_days(to_date, 1)

    listens_df = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
    table_name = 'user_{}_month'.format(entity)
    listens_df.createOrReplaceTempView(table_name)

    handler = entity_handler_map[entity]
    data = handler(table_name)

    messages = create_messages(data=data, entity=entity, stats_range='month',
                               from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    logger.debug("Done!")

    return messages


def get_entity_year(entity: str) -> Iterator[Optional[UserEntityStatMessage]]:
    """ Get the year top entity for all users """
    logger.debug("Calculating {}_year...".format(entity))

    to_date = get_latest_listen_ts()
    from_date = replace_days(replace_months(to_date, 1), 1)

    listens_df = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
    table_name = 'user_{}_year'.format(entity)
    listens_df.createOrReplaceTempView(table_name)

    handler = entity_handler_map[entity]
    data = handler(table_name)
    messages = create_messages(data=data, entity=entity, stats_range='year',
                               from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    logger.debug("Done!")

    return messages


def get_entity_all_time(entity: str) -> Iterator[Optional[UserEntityStatMessage]]:
    """ Get the all_time top entity for all users """
    logger.debug("Calculating {}_all_time...".format(entity))

    to_date = get_latest_listen_ts()
    from_date = datetime(LAST_FM_FOUNDING_YEAR, 1, 1)

    listens_df = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
    table_name = 'user_{}_all_time'.format(entity)
    listens_df.createOrReplaceTempView(table_name)

    handler = entity_handler_map[entity]
    data = handler(table_name)
    messages = create_messages(data=data, entity=entity, stats_range='all_time',
                               from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    logger.debug("Done!")

    return messages


def create_messages(data, entity: str, stats_range: str, from_ts: int, to_ts: int) -> Iterator[Optional[UserEntityStatMessage]]:
    """
    Create messages to send the data to the webserver via RabbitMQ

    Args:
        data (iterator): Data to sent to the webserver
        entity: The entity for which statistics are calculated, i.e 'artists',
            'releases' or 'recordings'
        stats_range: The range for which the statistics have been calculated
        from_ts: The UNIX timestamp of start time of the stats
        to_ts: The UNIX timestamp of end time of the stats

    Returns:
        messages: A list of messages to be sent via RabbitMQ
    """
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
                logger.warning("""Invalid entry present in {stats_range} top {entity} for
                                        user: {user_name}, skipping""".format(stats_range=stats_range, entity=entity,
                                                                              user_name=_dict['user_name']))
        try:
            model = UserEntityStatMessage(**{
                'musicbrainz_id': _dict['user_name'],
                'type': 'user_entity',
                'stats_range': stats_range,
                'from_ts': from_ts,
                'to_ts': to_ts,
                'data': entity_list,
                'entity': entity,
                'count': total_entity_count
            })
            result = model.dict(exclude_none=True)
            yield result
        except ValidationError:
            logger.error("""ValidationError while calculating {stats_range} top {entity} for user: {user_name}.
                                     Data: {data}""".format(stats_range=stats_range, entity=entity, user_name=_dict['user_name'],
                                                            data=json.dumps(_dict, indent=3)),
                                     exc_info=True)
            yield None
