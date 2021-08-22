from datetime import datetime

from listenbrainz_spark.stats import offset_days


def get_last_monday(date: datetime) -> datetime:
    """ Get date for Monday before 'date' """
    return offset_days(date, date.weekday())
