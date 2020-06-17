from calendar import monthrange
from datetime import datetime

from flask import current_app
from pyspark.sql.functions import collect_list, sort_array, struct
from pyspark.sql.types import (StringType, StructField, StructType,
                               TimestampType)

import listenbrainz_spark
from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.path import LISTENBRAINZ_DATA_DIRECTORY
from listenbrainz_spark.stats import (adjust_days, adjust_months, replace_days,
                                      replace_months, run_query)
from listenbrainz_spark.stats.user.utils import (filter_listens,
                                                 get_last_monday,
                                                 get_latest_listen_ts)
from listenbrainz_spark.utils import get_listens

time_range_schema = StructType((StructField('time_range', StringType()), StructField(
    'start', TimestampType()), StructField('end', TimestampType())))


def get_listening_activity(time_range: str):
    result = run_query("""
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

    iterator = result \
        .withColumn("listening_activity", struct("listen_count", "time_range")) \
        .groupBy("user_name") \
        .agg(collect_list("listening_activity").alias("listening_activity")) \
        .toLocalIterator()

    return iterator


def get_listening_activity_week():
    """ Get the weekly listening activity for all users """
    current_app.logger.debug("Calculating listening_activity_week")

    date = get_latest_listen_ts()
    to_date = get_last_monday(date)
    from_date = adjust_days(to_date, 7)
    time_range = []
    for offset in range(0, 7):
        day = adjust_days(from_date, offset, shift_backwards=False)
        time_range.append([day.strftime('%A'), day, _get_day_end(day)])

    time_range_df = listenbrainz_spark.session.createDataFrame(time_range, time_range_schema)
    time_range_df.createOrReplaceTempView('time_range')

    listens_df = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
    listens_df.createOrReplaceTempView('listens')

    data = get_listening_activity('week')
    messages = create_messages(data=data, stats_range='week', from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    current_app.logger.debug("Done!")

    return messages


def get_listening_activity_month():
    """ Get the monthly listening activity for all users """
    current_app.logger.debug("Calculating listening_activity_month")

    to_date = get_latest_listen_ts()
    from_date = replace_days(to_date, 1)
    time_range = []
    for offset in range(1, to_date.day+1):
        day = replace_days(from_date, offset)
        time_range.append([day.strftime('%d'), day, _get_day_end(day)])

    time_range_df = listenbrainz_spark.session.createDataFrame(time_range, time_range_schema)
    time_range_df.createOrReplaceTempView('time_range')

    listens_df = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
    listens_df.createOrReplaceTempView('listens')

    data = get_listening_activity('month')
    messages = create_messages(data=data, stats_range='month', from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    current_app.logger.debug("Done!")

    return messages


def get_listening_activity_year():
    """ Get the yearly listening activity for all users """
    current_app.logger.debug("Calculating listening_activity_year")

    to_date = get_latest_listen_ts()
    from_date = datetime(to_date.year, 1, 1)
    time_range = []
    for offset in range(1, to_date.month+1):
        month = replace_months(from_date, offset)
        time_range.append([month.strftime('%B'), month, _get_month_end(month)])

    time_range_df = listenbrainz_spark.session.createDataFrame(time_range, time_range_schema)
    time_range_df.createOrReplaceTempView('time_range')

    listens_df = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
    listens_df.createOrReplaceTempView('listens')

    data = get_listening_activity('year')
    messages = create_messages(data=data, stats_range='year', from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    current_app.logger.debug("Done!")

    return messages


def get_listening_activity_all_time():
    """ Get the all_timely listening activity for all users """
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

    data = get_listening_activity('all_time')
    messages = create_messages(data=data, stats_range='all_time', from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    current_app.logger.debug("Done!")

    return messages


def create_messages(data, stats_range: str, from_ts: int, to_ts: int):
    """
    Create messages to send the data to webserver via RabbitMQ

    Args:
        data (iterator): Data to send to webserver

    Returns:
        messages (generator): A list of messages to be sent via RabbitMQ
    """
    for entry in data:
        _dict = entry.asDict(recursive=True)
        yield {
            'musicbrainz_id': _dict['user_name'],
            'type': 'user_listening_activity',
            'range': stats_range,
            'from_ts': from_ts,
            'to_ts': to_ts,
            'listening_activity': _dict['listening_activity']
        }


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
