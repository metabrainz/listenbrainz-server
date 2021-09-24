import json
import logging
from datetime import datetime
from typing import Iterator, Optional

from dateutil.relativedelta import relativedelta
from pydantic import ValidationError

import listenbrainz_spark
from data.model.user_listening_activity import UserListeningActivityStatMessage
from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.stats import (offset_days, offset_months, get_day_end,
                                      get_month_end, get_year_end,
                                      replace_days, run_query, get_last_monday)
from listenbrainz_spark.utils import get_listens_from_new_dump, get_latest_listen_ts
from pyspark.sql.functions import collect_list, sort_array, struct, lit
from pyspark.sql.types import (StringType, StructField, StructType,
                               TimestampType)

time_range_schema = StructType([
    StructField("time_range", StringType()),
    StructField("start", TimestampType()),
    StructField("end", TimestampType())
])


logger = logging.getLogger(__name__)


def get_listening_activity():
    """ Calculate number of listens for each user in time ranges given in the "time_range" table """
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
    result_without_zero_days.createOrReplaceTempView("result_without_zero_days")

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


def _calculate_listening_activity(stats_range: str, from_date: datetime, to_date: datetime,
                                  step: relativedelta, date_format: str, get_period_end: callable):
    logger.debug(f"Calculating listening_activity_{stats_range}")

    # Set time to 00:00
    from_date = datetime(from_date.year, from_date.month, from_date.day)
    time_range = []

    _date = from_date
    while _date < to_date:
        time_range.append([_date.strftime(date_format), _date, get_period_end(_date)])
        _date = _date + step

    time_range_df = listenbrainz_spark.session.createDataFrame(time_range, time_range_schema)
    time_range_df.createOrReplaceTempView("time_range")

    get_listens_from_new_dump(from_date, to_date).createOrReplaceTempView("listens")
    data = get_listening_activity()
    messages = create_messages(data=data, stats_range=stats_range, from_date=from_date, to_date=to_date)

    logger.debug("Done!")

    return messages


def get_listening_activity_week() -> Iterator[Optional[UserListeningActivityStatMessage]]:
    """ Calculate number of listens for an user on each day of the past and current week. """
    to_date = get_latest_listen_ts()
    from_date = offset_days(get_last_monday(to_date), 7)
    step = relativedelta(days=+1)
    return _calculate_listening_activity(stats_range="week", from_date=from_date, to_date=to_date,
                                         step=step, date_format="%A %d %B %Y", get_period_end=get_day_end)


def get_listening_activity_month() -> Iterator[Optional[UserListeningActivityStatMessage]]:
    """ Calculate number of listens for an user on each day of the past month and current month. """
    to_date = get_latest_listen_ts()
    from_date = offset_months(replace_days(to_date, 1), 1)
    step = relativedelta(days=+1)
    return _calculate_listening_activity(stats_range="month", from_date=from_date, to_date=to_date,
                                         step=step, date_format="%d %B %Y", get_period_end=get_day_end)


def get_listening_activity_year() -> Iterator[Optional[UserListeningActivityStatMessage]]:
    """ Calculate the number of listens for an user in each month of the past and current year. """
    to_date = get_latest_listen_ts()
    from_date = datetime(to_date.year - 1, 1, 1)
    step = relativedelta(months=+1)
    return _calculate_listening_activity(stats_range="year", from_date=from_date, to_date=to_date,
                                         step=step, date_format="%B %Y", get_period_end=get_month_end)


def get_listening_activity_all_time() -> Iterator[Optional[UserListeningActivityStatMessage]]:
    """ Calculate the number of listens for an user in each year starting from LAST_FM_FOUNDING_YEAR (2002). """
    to_date = get_latest_listen_ts()
    from_date = datetime(LAST_FM_FOUNDING_YEAR, 1, 1)
    step = relativedelta(years=+1)
    return _calculate_listening_activity(stats_range="all_time", from_date=from_date, to_date=to_date,
                                         step=step, date_format="%Y", get_period_end=get_year_end)


def create_messages(data, stats_range: str, from_date: datetime, to_date: datetime) \
        -> Iterator[Optional[UserListeningActivityStatMessage]]:
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
            model = UserListeningActivityStatMessage(**{
                "musicbrainz_id": _dict["user_name"],
                "type": "user_listening_activity",
                "stats_range": stats_range,
                "from_ts": from_ts,
                "to_ts": to_ts,
                "data": _dict["listening_activity"]
            })
            result = model.dict(exclude_none=True)
            yield result
        except ValidationError:
            logger.error(f"""ValidationError while calculating {stats_range} listening_activity for user: 
            {_dict["user_name"]}. Data: {json.dumps(_dict, indent=3)}""", exc_info=True)
            yield None
