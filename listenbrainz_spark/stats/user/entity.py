from datetime import datetime

from flask import current_app

from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.path import LISTENBRAINZ_DATA_DIRECTORY
from listenbrainz_spark.stats import (adjust_days, replace_days,
                                      replace_months, run_query)
from listenbrainz_spark.stats.user.artist import get_artists
from listenbrainz_spark.stats.user.recording import get_recordings
from listenbrainz_spark.stats.user.release import get_releases
from listenbrainz_spark.stats.user.utils import (filter_listens,
                                                 get_last_monday,
                                                 get_latest_listen_ts)
from listenbrainz_spark.utils import get_listens

entity_handler_map = {
    'artists': get_artists,
    'releases': get_releases,
    'recordings': get_recordings
}


def get_entity_week(entity):
    """ Get the weekly top entity for all users """
    current_app.logger.debug("Calculating {}_week...".format(entity))

    date = get_latest_listen_ts()

    to_date = get_last_monday(date)
    from_date = adjust_days(to_date, 7)

    listens_df = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
    filtered_df = filter_listens(listens_df, from_date, to_date)
    table_name = 'user_{}_week'.format(entity)
    filtered_df.createOrReplaceTempView(table_name)

    handler = entity_handler_map[entity]
    data = handler(table_name)
    messages = create_messages(data=data, entity=entity, stats_range='week',
                               from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    current_app.logger.debug("Done!")

    return messages


def get_entity_month(entity):
    """ Get the month top entity for all users """
    current_app.logger.debug("Calculating {}_month...".format(entity))

    to_date = get_latest_listen_ts()
    from_date = replace_days(to_date, 1)

    listens_df = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
    table_name = 'user_{}_month'.format(entity)
    listens_df.createOrReplaceTempView(table_name)

    handler = entity_handler_map[entity]
    data = handler(table_name)

    messages = create_messages(data=data, entity=entity, stats_range='month',
                               from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    current_app.logger.debug("Done!")

    return messages


def get_entity_year(entity):
    """ Get the year top entity for all users """
    current_app.logger.debug("Calculating {}_year...".format(entity))

    to_date = get_latest_listen_ts()
    from_date = replace_days(replace_months(to_date, 1), 1)

    listens_df = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
    table_name = 'user_{}_year'.format(entity)
    listens_df.createOrReplaceTempView(table_name)

    handler = entity_handler_map[entity]
    data = handler(table_name)
    messages = create_messages(data=data, entity=entity, stats_range='year',
                               from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    current_app.logger.debug("Done!")

    return messages


def get_entity_all_time(entity):
    """ Get the all_time top entity for all users """
    current_app.logger.debug("Calculating {}_all_time...".format(entity))

    to_date = get_latest_listen_ts()
    from_date = datetime(LAST_FM_FOUNDING_YEAR, 1, 1)

    listens_df = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
    table_name = 'user_{}_all_time'.format(entity)
    listens_df.createOrReplaceTempView(table_name)

    handler = entity_handler_map[entity]
    data = handler(table_name)
    messages = create_messages(data=data, entity=entity, stats_range='all_time',
                               from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    current_app.logger.debug("Done!")

    return messages


def create_messages(data, entity, stats_range, from_ts, to_ts):
    """
    Create messages to send the data to the webserver via RabbitMQ

    Args:
        data (iterator): Data to sent to the webserver
        entity (str): The entity for which statistics are calculated, i.e 'artists',
            'releases' or 'recordings'
        stats_type (str): The type of statistics calculated
        stats_range (str): The range for which the statistics have been calculated
        from_ts (int): The UNIX timestamp of start time of the stats
        to_ts (int): The UNIX timestamp of end time of the stats

    Returns:
        messages (generator): A list of messages to be sent via RabbitMQ
    """
    for entry in data:
        _dict = entry.asDict(recursive=True)
        yield {
            'musicbrainz_id': _dict['user_name'],
            'type': 'user_entity',
            'range': stats_range,
            'from_ts': from_ts,
            'to_ts': to_ts,
            'data': _dict[entity],
            'entity': entity,
            'count': len(_dict[entity])
        }
