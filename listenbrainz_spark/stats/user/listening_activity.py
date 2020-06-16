from datetime import datetime

from flask import current_app
from pyspark.sql.functions import collect_list, sort_array, struct
from pyspark.sql.types import (StringType, StructField, StructType,
                               TimestampType)

from listenbrainz_spark import session, sql_context
from listenbrainz_spark.path import LISTENBRAINZ_DATA_DIRECTORY
from listenbrainz_spark.stats import (adjust_days, adjust_months, replace_days,
                                      replace_months, run_query)
from listenbrainz_spark.stats.user.utils import (filter_listens,
                                                 get_last_monday,
                                                 get_latest_listen_ts)
from listenbrainz_spark.utils import get_listens

time_range_schema = StringType((StructField('time_range', StringType()), StructField(
    'start', TimestampType()), StructField('end', TimestampType())))


def get_listening_activity(time_range: str):
    result = run_query("""
            SELECT listens.user_name
                 , time_range.time_range
                 , count({listens}.user_name) as listen_count
              FROM listens
              JOIN time_range
                ON listens.listened_at >= time_range.start
               AND listens.listened_at <= time_range.end
          GROUP BY listens.user_name
                 , time_range.time_range
            """)

    iterator = result \
        .withColumn(time_range, struct("listen_count", "time_range")) \
        .groupBy("user_name") \
        .agg(collect_list(time_range).alias(time_range)) \
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
        time_range.append([day.strftime('%A'), day, datetime(day.year, day.month, day.day, hour=23, minute=59, second=59)])

    time_range_df = session.createDataFrame(time_range, time_range_schema)
    time_range_df.createOrReplaceTempView('time_range')

    listens_df = get_listens(from_date, to_date, path=LISTENBRAINZ_DATA_DIRECTORY)
    listens_df.createOrReplaceTempView('listens')

    data = get_listening_activity('week')
    messages = create_messages(data)

    current_app.logger.debug("Done!")

    return messages


def get_listening_activity_month():
    """ Get the monthly listening activity for all users """
    current_app.logger.debug("Calculating listening_activity_month")

    to_date = get_latest_listen_ts()
    from_date = replace_days(to_date, 1)
    time_range = []
    for offset in range(1, to_date.day):
        day = replace_days(from_date, offset)
        time_range.append([day.strftime('%A'), day, datetime(day.year, day.month, day.day, hour=23, minute=59, second=59)])

    time_range_df = session.createDataFrame(time_range, time_range_schema)
    time_range_df.createOrReplaceTempView('time_range')

    listens_df = get_listens(from_date, to_date, path=LISTENBRAINZ_DATA_DIRECTORY)
    listens_df.createOrReplaceTempView('listens')

    data = get_listening_activity('month')
    messages = create_messages(data)

    current_app.logger.debug("Done!")

    return messages


def get_listening_activity_year():
    """ Get the yearly listening activity for all users """
    current_app.logger.debug("Calculating listening_activity_year")

    to_date = get_latest_listen_ts()
    from_date = replace_days(to_date, 1)
    time_range = []
    for offset in range(1, to_date.day):
        day = replace_days(from_date, offset)
        time_range.append([day.strftime('%A'), day, datetime(day.year, day.year, day.day, hour=23, minute=59, second=59)])

    time_range_df = session.createDataFrame(time_range, time_range_schema)
    time_range_df.createOrReplaceTempView('time_range')

    listens_df = get_listens(from_date, to_date, path=LISTENBRAINZ_DATA_DIRECTORY)
    listens_df.createOrReplaceTempView('listens')

    data = get_listening_activity('year')
    messages = create_messages(data)

    current_app.logger.debug("Done!")

    return messages


def create_messages(data):
    pass
