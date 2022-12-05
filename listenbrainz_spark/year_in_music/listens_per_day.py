from datetime import datetime, date, time

from dateutil.relativedelta import relativedelta

import listenbrainz_spark
from listenbrainz_spark.stats.common.listening_activity import time_range_schema
from listenbrainz_spark.stats.user.listening_activity import calculate_listening_activity, create_messages
from listenbrainz_spark.utils import get_listens_from_new_dump


def calculate_listens_per_day(year):
    from_date = datetime(year, 1, 1)
    to_date = datetime.combine(date(year, 12, 31), time.max)
    step = relativedelta(days=+1)
    date_format = "%d %B %Y"

    time_range = []
    segment_start = from_date
    while segment_start < to_date:
        segment_formatted = segment_start.strftime(date_format)
        # calculate the time at which this period ends i.e. 1 microsecond before the next period's start
        # here, segment_start + step is next segment's start
        segment_end = segment_start + step + relativedelta(microseconds=-1)
        time_range.append([segment_formatted, segment_start, segment_end])
        segment_start = segment_start + step
    time_range_df = listenbrainz_spark.session.createDataFrame(time_range, time_range_schema)
    time_range_df.createOrReplaceTempView("time_range")

    listens = get_listens_from_new_dump(from_date, to_date)
    listens.createOrReplaceTempView("listens")

    data = calculate_listening_activity()
    stats = create_messages(data=data, stats_range="year_in_music", from_date=from_date,
                            to_date=to_date, message_type="year_in_music_listens_per_day")
    for message in stats:
        # yim stats are stored in postgres instead of couchdb so drop those messages for yim
        if message["type"] == "couchdb_data_start" or message["type"] == "couchdb_data_end":
            continue

        message["year"] = year
        yield message
