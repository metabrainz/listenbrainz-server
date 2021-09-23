import itertools
import json
import calendar
import logging
from datetime import datetime
from typing import Iterator, Optional

from pydantic import ValidationError

import listenbrainz_spark
from data.model.user_daily_activity import UserDailyActivityStatMessage
from listenbrainz_spark.stats import run_query, get_dates_for_stats_range
from listenbrainz_spark.utils import get_listens_from_new_dump
from pyspark.sql.functions import collect_list, sort_array, struct


logger = logging.getLogger(__name__)


def get_daily_activity():
    """ Calculate number of listens for each user in each hour. """

    # Genarate a dataframe containing hours of all days of the week
    weekdays = [calendar.day_name[day] for day in range(0, 7)]
    hours = [hour for hour in range(0, 24)]
    time_range = itertools.product(weekdays, hours)
    time_range_df = listenbrainz_spark.session.createDataFrame(time_range, schema=["day", "hour"])
    time_range_df.createOrReplaceTempView("time_range")

    # Truncate listened_at to day and hour to improve matching speed
    formatted_listens = run_query("""
                            SELECT user_name
                                 , date_format(listened_at, 'EEEE') as day
                                 , date_format(listened_at, 'H') as hour
                              FROM listens
                              """)

    formatted_listens.createOrReplaceTempView("listens")

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
    return _get_daily_activity_range("week")


def get_daily_activity_month() -> Iterator[Optional[UserDailyActivityStatMessage]]:
    """ Calculate number of listens for an user per hour on each day of week of the current month. """
    return _get_daily_activity_range("month")


def get_daily_activity_year() -> Iterator[Optional[UserDailyActivityStatMessage]]:
    """ Calculate number of listens for an user per hour on each day of week of the current year. """
    return _get_daily_activity_range("year")


def get_daily_activity_all_time() -> Iterator[Optional[UserDailyActivityStatMessage]]:
    """ Calculate number of listens for an user per hour on each day of week. """
    return _get_daily_activity_range("all_time")


def _get_daily_activity_range(stats_range: str) -> Iterator[Optional[UserDailyActivityStatMessage]]:
    """ Calculate number of listens for an user for the specified time range """
    logger.debug(f"Calculating daily_activity_{stats_range}")

    from_date, to_date = get_dates_for_stats_range(stats_range)
    get_listens_from_new_dump(from_date, to_date).createOrReplaceTempView("listens")
    data = get_daily_activity()
    messages = create_messages(data=data, stats_range=stats_range, from_date=from_date, to_date=to_date)

    logger.debug("Done!")

    return messages


def create_messages(data, stats_range: str, from_date: datetime, to_date: datetime) \
        -> Iterator[Optional[UserDailyActivityStatMessage]]:
    """
    Create messages to send the data to webserver via RabbitMQ

    Args:
        data: Data to send to webserver
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
        try:
            model = UserDailyActivityStatMessage(**{
                "musicbrainz_id": _dict["user_name"],
                "type": "user_daily_activity",
                "from_ts": from_ts,
                "to_ts": to_ts,
                "stats_range": stats_range,
                "data": _dict["daily_activity"]
            })
            result = model.dict(exclude_none=True)
            yield result
        except ValidationError:
            logger.error(f"""ValidationError while calculating {stats_range} daily_activity for user:
            {_dict["user_name"]}. Data: {json.dumps(_dict, indent=3)}""", exc_info=True)
            yield None
