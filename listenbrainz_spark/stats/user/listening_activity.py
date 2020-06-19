from calendar import monthrange
from datetime import datetime
from typing import Iterator

from flask import current_app

import listenbrainz_spark
from listenbrainz_spark.stats.user.model.user_listening_activity import \
    UserListeningActivityStatMessage
from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.path import LISTENBRAINZ_DATA_DIRECTORY
from listenbrainz_spark.stats import (adjust_days, adjust_months, replace_days,
                                      replace_months, run_query)
from listenbrainz_spark.stats.user.utils import (filter_listens,
                                                 get_last_monday,
                                                 get_latest_listen_ts)
from listenbrainz_spark.utils import get_listens
from pyspark.sql.functions import collect_list, sort_array, struct
from pyspark.sql.types import (StringType, StructField, StructType,
                               TimestampType)

time_range_schema = StructType((StructField('time_range', StringType()), StructField(
    'start', TimestampType()), StructField('end', TimestampType())))


def get_listening_activity():
    """ Calculate number of listens for each user in time ranges given in the 'time_range' table """
    int_result = run_query("""
            SELECT listens.user_name
                 , time_range.time_range
                 , count(listens.user_name) as listen_count
              FROM listens
              JOIN time_range
                ON listens.listened_at >= time_range.start
               AND listens.listened_at <= time_range.end
          GROUP BY listens.user_name
                 , time_range.time_range
            """)
    int_result.createOrReplaceTempView('int_result')

    result = run_query("""
            SELECT dist_user_name.user_name
                 , time_range.time_range
                 , to_unix_timestamp(time_range.start) as from_ts
                 , to_unix_timestamp(time_range.end) as to_ts
                 , ifnull(int_result.listen_count, 0) as listen_count
              FROM (SELECT DISTINCT user_name FROM listens) dist_user_name
        CROSS JOIN time_range
         LEFT JOIN int_result
                ON int_result.user_name = dist_user_name.user_name
               AND int_result.time_range = time_range.time_range
            """)

    iterator = result \
        .withColumn("listening_activity", struct("from_ts", "to_ts", "listen_count", "time_range")) \
        .groupBy("user_name") \
        .agg(sort_array(collect_list("listening_activity")).alias("listening_activity")) \
        .toLocalIterator()

    return iterator


def get_listening_activity_week() -> Iterator[UserListeningActivityStatMessage]:
    """ Calculate number of listens for an user on each day of the past and current week. """
    current_app.logger.debug("Calculating listening_activity_week")

    date = get_latest_listen_ts()
    to_date = get_last_monday(date)
    # Set time to 00:00
    to_date = datetime(to_date.year, to_date.month, to_date.day)
    from_date = day = adjust_days(to_date, 14)

    # Genarate a dataframe containing days of last and current week along with start and end time
    time_range = []
    while day < to_date:
        time_range.append([day.strftime('%A %d %B %Y'), day, _get_day_end(day)])
        day = adjust_days(day, 1, shift_backwards=False)

    time_range_df = listenbrainz_spark.session.createDataFrame(time_range, time_range_schema)
    time_range_df.createOrReplaceTempView('time_range')

    listens_df = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
    listens_df.createOrReplaceTempView('listens')

    data = get_listening_activity()
    messages = create_messages(data=data, stats_range='week', from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    current_app.logger.debug("Done!")

    return messages


def get_listening_activity_month() -> Iterator[UserListeningActivityStatMessage]:
    """ Calculate number of listens for an user on each day of the past month and current month. """
    current_app.logger.debug("Calculating listening_activity_month")

    to_date = get_latest_listen_ts()
    # Set time to 00:00
    to_date = datetime(to_date.year, to_date.month, to_date.day)
    from_date = day = adjust_months(replace_days(to_date, 1), 1)

    # Genarate a dataframe containing days of last and current month along with start and end time
    time_range = []
    while day < to_date:
        time_range.append([day.strftime('%d %B %Y'), day, _get_day_end(day)])
        day = adjust_days(day, 1, shift_backwards=False)

    time_range_df = listenbrainz_spark.session.createDataFrame(time_range, time_range_schema)
    time_range_df.createOrReplaceTempView('time_range')

    listens_df = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
    listens_df.createOrReplaceTempView('listens')

    data = get_listening_activity()
    messages = create_messages(data=data, stats_range='month', from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    current_app.logger.debug("Done!")

    return messages


def get_listening_activity_year() -> Iterator[UserListeningActivityStatMessage]:
    """ Calculate the number of listens for an user in each month of the past and current year. """
    current_app.logger.debug("Calculating listening_activity_year")

    to_date = get_latest_listen_ts()
    from_date = month = datetime(to_date.year-1, 1, 1)
    time_range = []

    # Genarate a dataframe containing months of last and current year along with start and end time
    while month < to_date:
        time_range.append([month.strftime('%B %Y'), month, _get_month_end(month)])
        month = adjust_months(month, 1, shift_backwards=False)

    time_range_df = listenbrainz_spark.session.createDataFrame(time_range, time_range_schema)
    time_range_df.createOrReplaceTempView('time_range')

    listens_df = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
    listens_df.createOrReplaceTempView('listens')

    data = get_listening_activity()
    messages = create_messages(data=data, stats_range='year', from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    current_app.logger.debug("Done!")

    return messages


def get_listening_activity_all_time() -> Iterator[UserListeningActivityStatMessage]:
    """ Calculate the number of listens for an user in each year starting from LAST_FM_FOUNDING_YEAR (2002). """
    current_app.logger.debug("Calculating listening_activity_all_time")

    to_date = get_latest_listen_ts()
    from_date = datetime(LAST_FM_FOUNDING_YEAR, 1, 1)

    time_range = []
    for year in range(from_date.year, to_date.year+1):
        time_range.append([str(year), datetime(year, 1, 1), _get_year_end(year)])

    time_range_df = listenbrainz_spark.session.createDataFrame(time_range, time_range_schema)
    time_range_df.createOrReplaceTempView('time_range')

    listens_df = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
    listens_df.createOrReplaceTempView('listens')

    data = get_listening_activity()
    messages = create_messages(data=data, stats_range='all_time', from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    current_app.logger.debug("Done!")

    return messages


def create_messages(data, stats_range: str, from_ts: int, to_ts: int) -> Iterator[UserListeningActivityStatMessage]:
    """
    Create messages to send the data to webserver via RabbitMQ

    Args:
        data: Data to send to webserver

    Returns:
        messages: A list of messages to be sent via RabbitMQ
    """
    for entry in data:
        _dict = entry.asDict(recursive=True)
        yield UserListeningActivityStatMessage(**{
            'musicbrainz_id': _dict['user_name'],
            'type': 'user_listening_activity',
            'range': stats_range,
            'from_ts': from_ts,
            'to_ts': to_ts,
            'listening_activity': _dict['listening_activity']
        })


def _get_day_end(day: datetime) -> datetime:
    """ Returns a datetime object denoting the end of the day """
    return datetime(day.year, day.month, day.day, hour=23, minute=59, second=59)


def _get_month_end(month: datetime) -> datetime:
    """ Returns a datetime object denoting the end of the month """
    _, num_of_days = monthrange(month.year, month.month)
    return datetime(month.year, month.month, num_of_days, hour=23, minute=59, second=59)


def _get_year_end(year: int) -> datetime:
    """ Returns a datetime object denoting the end of the year """
    return datetime(year, month=12, day=31, hour=23, minute=59, second=59)
