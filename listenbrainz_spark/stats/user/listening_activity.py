import json
import logging
from datetime import datetime
from typing import Iterator, Optional

from pydantic import ValidationError

import listenbrainz_spark
from data.model.user_listening_activity import UserListeningActivityStatMessage
from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.exceptions import HDFSException
from listenbrainz_spark.path import LISTENBRAINZ_DATA_DIRECTORY
from listenbrainz_spark.stats import (offset_days, offset_months, get_day_end,
                                      get_month_end, get_year_end,
                                      replace_days, replace_months, run_query)
from listenbrainz_spark.stats.utils import (filter_listens,
                                            get_last_monday,
                                            get_latest_listen_ts)
from listenbrainz_spark.utils import get_listens
from pyspark.sql.functions import collect_list, sort_array, struct, lit
from pyspark.sql.types import (StringType, StructField, StructType,
                               TimestampType)

time_range_schema = StructType((StructField('time_range', StringType()), StructField(
    'start', TimestampType()), StructField('end', TimestampType())))


logger = logging.getLogger(__name__)


def get_listening_activity():
    """ Calculate number of listens for each user in time ranges given in the 'time_range' table """
    # Calculate the number of listens in each time range for each user except the time ranges which have zero listens.
    result_without_zero_days = run_query("""
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
    result_without_zero_days.createOrReplaceTempView('result_without_zero_days')

    # Add the time ranges which have zero listens to the previous dataframe
    result = run_query("""
            SELECT dist_user_name.user_name
                 , time_range.time_range
                 , to_unix_timestamp(time_range.start) as from_ts
                 , to_unix_timestamp(time_range.end) as to_ts
                 , ifnull(result_without_zero_days.listen_count, 0) as listen_count
              FROM (SELECT DISTINCT user_name FROM listens) dist_user_name
        CROSS JOIN time_range
         LEFT JOIN result_without_zero_days
                ON result_without_zero_days.user_name = dist_user_name.user_name
               AND result_without_zero_days.time_range = time_range.time_range
            """)

    # Create a table with a list of time ranges and corresponding listen count for each user
    iterator = result \
        .withColumn("listening_activity", struct("from_ts", "to_ts", "listen_count", "time_range")) \
        .groupBy("user_name") \
        .agg(sort_array(collect_list("listening_activity")).alias("listening_activity")) \
        .toLocalIterator()

    return iterator


def get_listening_activity_week() -> Iterator[Optional[UserListeningActivityStatMessage]]:
    """ Calculate number of listens for an user on each day of the past and current week. """
    logger.debug("Calculating listening_activity_week")

    to_date = get_latest_listen_ts()
    from_date = offset_days(get_last_monday(to_date), 7)
    # Set time to 00:00
    from_date = datetime(from_date.year, from_date.month, from_date.day)
    day = from_date

    # Genarate a dataframe containing days of last and current week along with start and end time
    time_range = []
    while day < to_date:
        time_range.append([day.strftime('%A %d %B %Y'), day, get_day_end(day)])
        day = offset_days(day, 1, shift_backwards=False)

    time_range_df = listenbrainz_spark.session.createDataFrame(time_range, time_range_schema)
    time_range_df.createOrReplaceTempView('time_range')

    _get_listens(from_date, to_date)

    data = get_listening_activity()
    messages = create_messages(data=data, stats_range='week', from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    logger.debug("Done!")

    return messages


def get_listening_activity_month() -> Iterator[Optional[UserListeningActivityStatMessage]]:
    """ Calculate number of listens for an user on each day of the past month and current month. """
    logger.debug("Calculating listening_activity_month")

    to_date = get_latest_listen_ts()
    from_date = offset_months(replace_days(to_date, 1), 1)
    # Set time to 00:00
    from_date = datetime(from_date.year, from_date.month, from_date.day)
    day = from_date

    # Genarate a dataframe containing days of last and current month along with start and end time
    time_range = []
    while day < to_date:
        time_range.append([day.strftime('%d %B %Y'), day, get_day_end(day)])
        day = offset_days(day, 1, shift_backwards=False)

    time_range_df = listenbrainz_spark.session.createDataFrame(time_range, time_range_schema)
    time_range_df.createOrReplaceTempView('time_range')

    _get_listens(from_date, to_date)

    data = get_listening_activity()
    messages = create_messages(data=data, stats_range='month', from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    logger.debug("Done!")

    return messages


def get_listening_activity_year() -> Iterator[Optional[UserListeningActivityStatMessage]]:
    """ Calculate the number of listens for an user in each month of the past and current year. """
    logger.debug("Calculating listening_activity_year")

    to_date = get_latest_listen_ts()
    from_date = datetime(to_date.year-1, 1, 1)
    month = datetime(to_date.year-1, 1, 1)
    time_range = []

    # Genarate a dataframe containing months of last and current year along with start and end time
    while month < to_date:
        time_range.append([month.strftime('%B %Y'), month, get_month_end(month)])
        month = offset_months(month, 1, shift_backwards=False)

    time_range_df = listenbrainz_spark.session.createDataFrame(time_range, time_range_schema)
    time_range_df.createOrReplaceTempView('time_range')

    _get_listens(from_date, to_date)

    data = get_listening_activity()
    messages = create_messages(data=data, stats_range='year', from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    logger.debug("Done!")

    return messages


def get_listening_activity_all_time() -> Iterator[Optional[UserListeningActivityStatMessage]]:
    """ Calculate the number of listens for an user in each year starting from LAST_FM_FOUNDING_YEAR (2002). """
    logger.debug("Calculating listening_activity_all_time")

    to_date = get_latest_listen_ts()
    from_date = datetime(LAST_FM_FOUNDING_YEAR, 1, 1)

    result_without_zero_years = None
    for year in range(from_date.year, to_date.year+1):
        year_start = datetime(year, 1, 1)
        year_end = get_year_end(year)
        try:
            _get_listens(year_start, year_end)
        except HDFSException:
            # Skip if no listens present in df
            continue
        year_df = run_query("""
                    SELECT user_name,
                           count(user_name) as listen_count
                      FROM listens
                  GROUP BY user_name
                  """)
        year_df = year_df.withColumn('time_range', lit(str(year))).withColumn(
            'from_ts', lit(year_start.timestamp())).withColumn('to_ts', lit(year_end.timestamp()))
        result_without_zero_years = result_without_zero_years.union(year_df) if result_without_zero_years else year_df

    # Create a table with a list of time ranges and corresponding listen count for each user
    data = result_without_zero_years \
        .withColumn("listening_activity", struct("from_ts", "to_ts", "listen_count", "time_range")) \
        .groupBy("user_name") \
        .agg(sort_array(collect_list("listening_activity")).alias("listening_activity")) \
        .toLocalIterator()

    messages = create_messages(data=data, stats_range='all_time', from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    logger.debug("Done!")

    return messages


def create_messages(data, stats_range: str, from_ts: int, to_ts: int) -> Iterator[Optional[UserListeningActivityStatMessage]]:
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
            model = UserListeningActivityStatMessage(**{
                'musicbrainz_id': _dict['user_name'],
                'type': 'user_listening_activity',
                'stats_range': stats_range,
                'from_ts': from_ts,
                'to_ts': to_ts,
                'listening_activity': _dict['listening_activity']
            })
            result = model.dict(exclude_none=True)
            yield result
        except ValidationError:
            logger.error("""ValidationError while calculating {stats_range} listening_activity for user: {user_name}.
                                     Data: {data}""".format(stats_range=stats_range, user_name=_dict['user_name'],
                                                            data=json.dumps(_dict, indent=3)),
                                     exc_info=True)
            yield None


def _get_listens(from_date: datetime, to_date: datetime):
    listens_df = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
    listens_df.createOrReplaceTempView('listens')
