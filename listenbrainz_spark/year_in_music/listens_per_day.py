from datetime import datetime, date, time

from listenbrainz_spark.stats.user.listening_activity import calculate_listening_activity, create_messages
from listenbrainz_spark.utils import get_listens_from_new_dump


def calculate_listens_per_day(year):
    from_date = datetime(year, 1, 1)
    to_date = datetime.combine(date(year, 12, 31), time.max)
    listens = get_listens_from_new_dump(from_date, to_date)
    listens.createOrReplaceTempView("listens")

    data = calculate_listening_activity()
    return create_messages(data=data, stats_range="year_in_music",
                           from_date=from_date, to_date=to_date,
                           message_type="year_in_music_listens_per_day")
