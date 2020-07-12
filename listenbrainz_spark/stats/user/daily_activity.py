import json
from datetime import datetime
from typing import Iterator, Optional

from flask import current_app
from pydantic import ValidationError

import listenbrainz_spark
from data.model.user_daily_activity import UserDailyActivityStatMessage
from listenbrainz_spark.path import LISTENBRAINZ_DATA_DIRECTORY
from listenbrainz_spark.stats import adjust_days, run_query
from listenbrainz_spark.stats.user.utils import (filter_listens,
                                                 get_last_monday,
                                                 get_latest_listen_ts)
from listenbrainz_spark.utils import get_listens
from pyspark.sql.functions import collect_list, sort_array, struct, lit
from pyspark.sql.types import (StringType, StructField, StructType,
                               TimestampType)

time_range_schema = StructType((StructField('time_range', StringType()), StructField(
    'start', TimestampType()), StructField('end', TimestampType())))


def get_daily_activity() -> Iterator[Optional[UserDailyActivityStatMessage]]:
    """ Calculate number of listens for each user in each hour of the last week """
    current_app.logger.debug("Calculating listening_activity_week")

    date = get_latest_listen_ts()
    # Set time to 00:00
    to_date = get_last_monday(date)
    from_date = adjust_days(to_date, 7)
    day = from_date

    # Genarate a dataframe containing hours of all days of last week week along with start and end time
    time_range = []
    while day < to_date:
        for hour in range(0, 24):
            hour_start = datetime(day.year, day.month, day.day, hour=hour)
            hour_end = datetime(day.year, day.month, day.day, hour=(hour+1) % 24)
            time_range.append([hour_start.strftime('%H %A'), hour_start, hour_end])

    time_range_df = listenbrainz_spark.session.createDataFrame(time_range, time_range_schema)
    time_range_df.createOrReplaceTempView('time_range')

    listens_df = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
    filtered_df = filter_listens(listens_df, from_date, to_date)

    filtered_df.createOrReplaceTempView('listens')

    # Calculate the number of listens in each time range for each user except the time ranges which have zero listens.
    result = run_query("""
            SELECT listens.user_name
                 , time_range.time_range
                 , to_unix_timestamp(time_range.start) as from_ts
                 , to_unix_timestamp(time_range.end) as to_ts
                 , count(listens.user_name) as listen_count
              FROM listens
              JOIN time_range
                ON listens.listened_at >= time_range.start
               AND listens.listened_at <= time_range.end
          GROUP BY listens.user_name
                 , time_range.time_range
            """)

    # Create a table with a list of time ranges and corresponding listen count for each user
    data = result \
        .withColumn("daily_activity", struct("from_ts", "to_ts", "listen_count", "time_range")) \
        .groupBy("user_name") \
        .agg(sort_array(collect_list("listening_activity")).alias("listening_activity")) \
        .toLocalIterator()

    messages = create_messages(data=data, from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    current_app.logger.debug("Done!")

    return messages


def create_messages(data, from_ts: int, to_ts: int) -> Iterator[Optional[UserDailyActivityStatMessage]]:
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
                'daily_activity': _dict['daily_activity']
            })
            result = model.dict(exclude_none=True)
            yield result
        except ValidationError:
            current_app.logger.error("""ValidationError while calculating daily_activity for user: {user_name}.
                                     Data: {data}""".format(user_name=_dict['user_name'],
                                                            data=json.dumps(_dict, indent=3)),
                                     exc_info=True)
            yield None
