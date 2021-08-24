import itertools
import json
import calendar
import logging
from datetime import datetime
from typing import Iterator, Optional

from pydantic import ValidationError

import listenbrainz_spark
from data.model.user_daily_activity import UserDailyActivityStatMessage
from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.path import LISTENBRAINZ_DATA_DIRECTORY
from listenbrainz_spark.stats import offset_days, replace_days, run_query
from listenbrainz_spark.stats.utils import (filter_listens,
                                            get_last_monday,
                                            get_latest_listen_ts)
from listenbrainz_spark.utils import get_listens
from pyspark.sql.functions import collect_list, sort_array, struct


logger = logging.getLogger(__name__)


def get_daily_activity():
    """ Calculate number of listens for each user in each hour. """

    # Genarate a dataframe containing hours of all days of the week
    weekdays = [calendar.day_name[day] for day in range(0, 7)]
    hours = [hour for hour in range(0, 24)]
    time_range = itertools.product(weekdays, hours)
    time_range_df = listenbrainz_spark.session.createDataFrame(time_range, schema=["day", "hour"])
    time_range_df.createOrReplaceTempView('time_range')

    # Truncate listened_at to day and hour to improve matching speed
    formatted_listens = run_query("""
                            SELECT user_name
                                 , date_format(listened_at, 'EEEE') as day
                                 , date_format(listened_at, 'H') as hour
                              FROM listens
                              """)

    formatted_listens.createOrReplaceTempView('listens')

    # Calculate the number of listens in each time range for each user except the time ranges which have zero listens.
    result = run_query("""
                SELECT listens.user_name
                     , time_range.day
                     , time_range.hour
                     , count(*) as listen_count
                  FROM listens
                  JOIN time_range
                    ON listens.day == time_range.day
                   AND listens.hour == time_range.hour
              GROUP BY listens.user_name
                     , time_range.day
                     , time_range.hour
                  """)

    # Create a table with a list of time ranges and corresponding listen count for each user
    iterator = result \
        .withColumn("daily_activity", struct("hour", "day", "listen_count")) \
        .groupBy("user_name") \
        .agg(sort_array(collect_list("daily_activity")).alias("daily_activity")) \
        .toLocalIterator()

    return iterator


def get_daily_activity_week() -> Iterator[Optional[UserDailyActivityStatMessage]]:
    """ Calculate number of listens for an user per hour on each day of the past week. """
    logger.debug("Calculating daily_activity_week")

    date = get_latest_listen_ts()
    to_date = get_last_monday(date)
    from_date = offset_days(to_date, 7)

    _get_listens(from_date, to_date)

    data = get_daily_activity()

    messages = create_messages(data=data, stats_range='week', from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    logger.debug("Done!")

    return messages


def get_daily_activity_month() -> Iterator[Optional[UserDailyActivityStatMessage]]:
    """ Calculate number of listens for an user per hour on each day of week of the current month. """
    logger.debug("Calculating daily_activity_month")

    to_date = get_latest_listen_ts()
    from_date = replace_days(to_date, 1)
    # Set time to 00:00
    from_date = datetime(from_date.year, from_date.month, from_date.day)

    _get_listens(from_date, to_date)

    data = get_daily_activity()
    messages = create_messages(data=data, stats_range='month', from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    logger.debug("Done!")

    return messages


def get_daily_activity_year() -> Iterator[Optional[UserDailyActivityStatMessage]]:
    """ Calculate number of listens for an user per hour on each day of week of the current year. """
    logger.debug("Calculating daily_activity_year")

    to_date = get_latest_listen_ts()
    from_date = datetime(to_date.year, 1, 1)

    _get_listens(from_date, to_date)

    data = get_daily_activity()
    messages = create_messages(data=data, stats_range='year', from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    logger.debug("Done!")

    return messages


def get_daily_activity_all_time() -> Iterator[Optional[UserDailyActivityStatMessage]]:
    """ Calculate number of listens for an user per hour on each day of week. """
    logger.debug("Calculating daily_activity_all_time")

    to_date = get_latest_listen_ts()
    from_date = datetime(LAST_FM_FOUNDING_YEAR, 1, 1)

    _get_listens(from_date, to_date)

    data = get_daily_activity()
    messages = create_messages(data=data, stats_range='all_time', from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    logger.debug("Done!")

    return messages


def create_messages(data, stats_range: str, from_ts: int, to_ts: int) -> Iterator[Optional[UserDailyActivityStatMessage]]:
    """
    Create messages to send the data to webserver via RabbitMQ

    Args:
        data: Data to send to webserver

    Returns:
        messages: A list of messages to be sent via RabbitMQ
    """
    for entry in data:
        _dict = entry.asDict(recursive=True)
        try:
            model = UserDailyActivityStatMessage(**{
                'musicbrainz_id': _dict['user_name'],
                'type': 'user_daily_activity',
                'from_ts': from_ts,
                'to_ts': to_ts,
                'stats_range': stats_range,
                'daily_activity': _dict['daily_activity']
            })
            result = model.dict(exclude_none=True)
            yield result
        except ValidationError:
            logger.error("""ValidationError while calculating {stats_range} daily_activity for user: {user_name}.
                                     Data: {data}""".format(stats_range=stats_range, user_name=_dict['user_name'],
                                                            data=json.dumps(_dict, indent=3)),
                                     exc_info=True)
            yield None


def _get_listens(from_date: datetime, to_date: datetime):
    listens = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
    filtered_listens = filter_listens(listens, from_date, to_date)
    filtered_listens.createOrReplaceTempView('listens')
