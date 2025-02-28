import logging
from datetime import datetime, time, date
from typing import Tuple

from dateutil.relativedelta import relativedelta, MO

import listenbrainz_spark
from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.listens.data import get_latest_listen_ts
from pyspark.sql.types import (StringType, StructField, StructType, TimestampType)

time_range_schema = StructType([
    StructField("time_range", StringType()),
    StructField("start", TimestampType()),
    StructField("end", TimestampType())
])

logger = logging.getLogger(__name__)


def _get_half_year_offset(_date: date) -> relativedelta:
    """ Given a month, returns the relativedelta offset to get
    the beginning date of the previous to previous half year."""
    month = _date.month
    if month <= 6:
        # currently, in Jan-Jun previous half year is last year's Jan-Jun
        return relativedelta(years=-1, month=1, day=1)
    else:
        # currently, in Jul-Dec previous half year is last year's Jul-Dec
        return relativedelta(years=-1, month=7, day=1)


def get_two_quarters_ago_offset(_date: date) -> relativedelta:
    """ Given a month, returns the relativedelta offset to get
    the beginning date of the previous to previous quarter.

    .. note:: there is similar function to calculate 1 quarter back
    in listenbrainz_spark.stats module which is used by other stats.
    However, here in listening_activity stats we need two quarters
    so that we can compare the quarter with the previous quarter of
    the same duration and .
    """
    month = _date.month
    if month <= 3:
        # currently, in Jan-Mar so 2 quarters ago is last year's Jul-Sep
        return relativedelta(years=-1, month=7, day=1)
    elif month <= 6:
        # currently, in Apr-Jun so 2 quarters ago is last year's Oct-Dec
        return relativedelta(years=-1, month=10, day=1)
    elif month <= 9:
        # currently, in Jul-Sep so 2 quarters ago is Jan-Mar
        return relativedelta(month=1, day=1)
    else:
        # currently, in Oct-Dec so 2 quarters ago is Apr-Jun
        return relativedelta(month=4, day=1)


def get_time_range_bounds(stats_range: str, year: int = None) -> Tuple[datetime, datetime, relativedelta, str, str]:
    """ Returns the start time, end time, segment step size, python date format and spark
     date format to use for calculating the listening activity stats

     We need both python date and spark date format because site wide listening activity uses
     it. See the site wide listening activity query for details.

     Python date format reference: https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes
     Spark date format reference: https://spark.apache.org/docs/latest/sql-ref-datetime-pattern.html

     If stats_range is set to year_in_music then the year must also be provided.

    .. note::

        other stats uses a different function (get_dates_for_stats_range) to calculate
        time ranges. if making modifications here, remember to check and update that as well
    """
    latest_listen_ts = get_latest_listen_ts()

    if stats_range == "year_in_music":
        if year is None:
            raise ValueError("year is required when stats_range is set to year_in_music")
        from_date = datetime(year, 1, 1)
        to_date = datetime.combine(date(year, 12, 31), time.max)
        step = relativedelta(days=+1)
        date_format = "%d %B %Y"
        spark_date_format = "dd MMMM y"
        return from_date, to_date, step, date_format, spark_date_format

    if stats_range == "all_time":
        # all_time stats range is easy, just return time from LASTFM founding
        # to the latest listen we have in spark
        from_date = datetime(LAST_FM_FOUNDING_YEAR, 1, 1)
        to_date = latest_listen_ts
        # compute listening activity on annual basis
        step = relativedelta(years=+1)
        date_format = "%Y"
        spark_date_format = "y"
        return from_date, to_date, step, date_format, spark_date_format

    # If we had used datetime.now or date.today here and the data in spark
    # became outdated due to some reason, empty stats would be sent to LB.
    # Hence, we use get_latest_listen_ts to get the time of the latest listen
    # in spark and so that instead of no stats, outdated stats are calculated.
    latest_listen_date = latest_listen_ts.date()

    # "this" time ranges, these count stats for the ongoing time period till date
    if stats_range.startswith("this"):
        if stats_range == "this_week":
            # if today is a monday then from_offset is monday of 2 weeks ago
            # otherwise from_offset is monday of last week
            from_offset = relativedelta(weeks=-1, days=-1, weekday=MO(-1))
            # compute listening activity for each day, include weekday in date format
            step = relativedelta(days=+1)
            date_format = "%A %d %B %Y"
            spark_date_format = "EEEE dd MMMM y"
        elif stats_range == "this_month":
            # if today is 1st then 1st of 2 months ago otherwise the 1st of last month
            from_offset = relativedelta(months=-2) if latest_listen_date.day == 1 else relativedelta(months=-1, day=1)
            # compute listening activity for each day but no weekday
            step = relativedelta(days=+1)
            date_format = "%d %B %Y"
            spark_date_format = "dd MMMM y"
        else:
            # if today is the 1st of the year, then still show last year stats
            if latest_listen_date.day == 1 and latest_listen_date.month == 1:
                from_offset = relativedelta(years=-2)
            else:
                from_offset = relativedelta(years=-1, month=1, day=1)
            step = relativedelta(months=+1)
            # compute listening activity for each month
            date_format = "%B %Y"
            spark_date_format = "MMMM y"

        from_date = latest_listen_date + from_offset

        # set time to 00:00
        from_date = datetime.combine(from_date, time.min)
        to_date = datetime.combine(latest_listen_date, time.min)
        return from_date, to_date, step, date_format, spark_date_format

    # following are "last" week/month/year stats, here we want the stats of the
    # previous week/month/year and *not* from 7 days ago to today so on.

    # from_offset: this is applied to the latest_listen_date to get from_date
    # to_offset: this is applied to from_date to get to_date
    if stats_range == "week":
        from_offset = relativedelta(weeks=-2, weekday=MO(-1))
        to_offset = relativedelta(weeks=+2)
        # compute listening activity for each day, include weekday in date format
        step = relativedelta(days=+1)
        date_format = "%A %d %B %Y"
        spark_date_format = "EEEE dd MMMM y"
    elif stats_range == "month":
        from_offset = relativedelta(months=-2, day=1)  # start of the previous to previous month
        to_offset = relativedelta(months=+2)
        # compute listening activity for each day but no weekday
        step = relativedelta(days=+1)
        date_format = "%d %B %Y"
        spark_date_format = "dd MMMM y"
    elif stats_range == "quarter":
        from_offset = get_two_quarters_ago_offset(latest_listen_date)
        to_offset = relativedelta(months=+6)
        step = relativedelta(days=+1)
        date_format = "%d %B %Y"
        spark_date_format = "dd MMMM y"
    elif stats_range == "half_yearly":
        from_offset = _get_half_year_offset(latest_listen_date)
        to_offset = relativedelta(months=+12)
        step = relativedelta(months=+1)
        date_format = "%B %Y"
        spark_date_format = "MMMM y"
    else:  # year
        from_offset = relativedelta(years=-2, month=1, day=1)  # start of the previous to previous year
        to_offset = relativedelta(years=+2)
        step = relativedelta(months=+1)
        # compute listening activity for each month
        date_format = "%B %Y"
        spark_date_format = "MMMM y"

    from_date = latest_listen_date + from_offset
    to_date = from_date + to_offset

    # set time to 00:00
    from_date = datetime.combine(from_date, time.min)
    to_date = datetime.combine(to_date, time.min)

    return from_date, to_date, step, date_format, spark_date_format


def create_time_range_df(from_date, to_date, step, date_format, spark_date_format):
    """ Sets up time range buckets dataframe needed to calculate listening activity stats. """
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


def setup_time_range(stats_range: str, year: int = None) -> Tuple[datetime, datetime, relativedelta, str, str]:
    """
    Sets up time range buckets needed to calculate listening activity stats and
    returns the start and end time of the time range.

    The listening activity stats compare the number of listens in sub-segments
    of two time ranges of similar length. For example: consider the this_year
    stat range. It will count the listens for each month since the start of
    last year so that we can present a chart comparing the listen counts of
    the corresponding months of last year against this year. Also, this function
    will return 1st of last year as the start time and the current date as the
    end time in this example.
    """
    from_date, to_date, step, date_format, spark_date_format = get_time_range_bounds(stats_range, year)
    create_time_range_df(from_date, to_date, step, date_format, spark_date_format)
    return from_date, to_date, step, date_format, spark_date_format
