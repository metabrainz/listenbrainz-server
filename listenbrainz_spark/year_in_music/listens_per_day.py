from datetime import datetime, date, time

from dateutil.relativedelta import relativedelta

from listenbrainz_spark.stats.common.listening_activity import _create_time_range_df
from listenbrainz_spark.stats.user.listening_activity import calculate_listening_activity, create_messages
from listenbrainz_spark.utils import get_listens_from_dump


def calculate_listens_per_day(year):
    from_date = datetime(year, 1, 1)
    to_date = datetime.combine(date(year, 12, 31), time.max)
    step = relativedelta(days=+1)
    date_format = "%d %B %Y"
    spark_date_format = "dd MMMM y"

    _create_time_range_df(from_date, to_date, step, date_format, spark_date_format)
    listens = get_listens_from_dump(from_date, to_date)
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
