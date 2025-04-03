from calendar import monthrange
from datetime import datetime, time, date
from typing import Tuple

from dateutil.relativedelta import relativedelta, MO

import listenbrainz_spark
from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.exceptions import SQLException

from pyspark.sql.utils import *

from listenbrainz_spark.listens.data import get_latest_listen_ts

SITEWIDE_STATS_ENTITY_LIMIT = 1000  # number of top artists to retain in sitewide stats


def run_query(query):
    """ Returns dataframe that results from running the query.

        Args:
            query (str): SQL query to execute.

    Note:
        >> While dealing with SQL queries in pyspark, catch the outermost exceptions and not Py4JJavaError
           since it is the innermost exception raised. For all the final(outer) exceptions refer to:
           'https://github.com/apache/spark/blob/master/python/pyspark/sql/utils.py'.
           In all other cases where Py4JJavaError is the only exception raised, catch it as such.
        >> It is the responsibility of the caller to register tables etc.
    """
    try:
        processed_query = listenbrainz_spark.session.sql(query)
    except AnalysisException as err:
        raise SQLException('{}. Failed to analyze SQL query plan for\n{}\n{}'.format(type(err).__name__, query, str(err)))
    except ParseException as err:
        raise SQLException('{}. Failed to parse SQL command\n{}\n{}'.format(type(err).__name__, query, str(err)))
    except IllegalArgumentException as err:
        raise SQLException('{}. Passed an illegal or inappropriate argument to\n{}\n{}'.format(type(err).__name__, query,
                                                                                               str(err)))
    except StreamingQueryException as err:
        raise SQLException('{}. Exception that stopped a :class:`StreamingQuery`\n{}\n{}'.format(type(err).__name__, query,
                                                                                                 str(err)))
    except QueryExecutionException as err:
        raise SQLException('{}. Failed to execute a query{}\n{}'.format(type(err).__name__, query, str(err)))
    except UnknownException as err:
        raise SQLException('{}. An error occurred while executing{}\n{}'.format(type(err).__name__, query, str(err)))
    return processed_query


def replace_days(date, day):
    date = date.replace(day=day)
    return date


def replace_months(date, month):
    date = date.replace(month=month)
    return date


def offset_months(date, months, shift_backwards=True):
    """
    Args:
        date   :  The datetime object to be modified
        months :  Number of months the date has to be shifted
        shift_backwards:
                - If True the number of months are subtracted from the date
                - If False the number of months are added to the date

    Returns:
            A datetime object with the input date shifted by the number of months
    """
    if shift_backwards:
        date = date + relativedelta(months=-months)
    else:
        date = date + relativedelta(months=months)
    return date


def offset_days(date, days, shift_backwards=True):
    """
    Args:
        date   :  The datetime object to be modified
        days   :  Number of days the date has to be shifted
        shift_backwards:
                - If True the number of days are subtracted from the date
                - If False the number of days are added to the date
    Returns:
            A datetime object with the input date shifted by the number of days
    """
    if shift_backwards:
        date = date + relativedelta(days=-days)
    else:
        date = date + relativedelta(days=days)
    return date


def get_day_end(day: datetime) -> datetime:
    """ Returns a datetime object denoting the end of the day """
    return datetime(day.year, day.month, day.day, hour=23, minute=59, second=59, microsecond=999999)


def get_month_end(month: datetime) -> datetime:
    """ Returns a datetime object denoting the end of the month """
    _, num_of_days = monthrange(month.year, month.month)
    return datetime(month.year, month.month, num_of_days, hour=23, minute=59, second=59, microsecond=999999)


def get_year_end(year: datetime) -> datetime:
    """ Returns a datetime object denoting the end of the year """
    return datetime(year.year, month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)


def get_last_monday(date: datetime) -> datetime:
    """ Get date for Monday before 'date' """
    return offset_days(date, date.weekday())


def get_last_half_year_offset(_date: date) -> relativedelta:
    """ Given a month, returns the relativedelta offset to get
    the beginning date of the previous half year."""
    month = _date.month
    if month <= 6:
        # currently, in Jan-Jun previous half year is last year's Jul-Dec
        return relativedelta(years=-1, month=7, day=1)
    else:
        # currently, in Jul-Dec previous half year is Jan-Jun
        return relativedelta(month=1, day=1)


def get_last_quarter_offset(_date: date) -> relativedelta:
    """ Given a month, returns the relativedelta offset to get
    the beginning date of the previous quarter."""
    month = _date.month
    if month <= 3:
        # currently, in Jan-Mar, so previous quarter is last year's Oct-Dec
        return relativedelta(years=-1, month=10, day=1)
    elif month <= 6:
        # currently, in Apr-Jun previous is Jan-Mar
        return relativedelta(month=1, day=1)
    elif month <= 9:
        # currently, in Jul-Sep, previous is Apr-Jun
        return relativedelta(month=4, day=1)
    else:
        # currently, in Oct-Dec previous is Jul-Sep
        return relativedelta(month=7, day=1)


# listening activity stats uses a different function to calculate time ranges
# if making modifications here, remember to check and update that as well
def get_dates_for_stats_range(stats_range: str) -> Tuple[datetime, datetime]:
    """ Return the range of datetimes for which stats should be calculated.

        Args:
            stats_range: the stats range (week/month/year/all_time) for
                which to get datetimes.
    """
    latest_listen_ts = get_latest_listen_ts()
    if stats_range == "all_time":
        # all_time stats range is easy, just return time from LASTFM founding
        # to the latest listen we have in spark
        from_date = datetime(LAST_FM_FOUNDING_YEAR, 1, 1)
        to_date = latest_listen_ts
        return from_date, to_date

    # If we had used datetime.now or date.today here and the data in spark
    # became outdated due to some reason, empty stats would be sent to LB.
    # Hence, we use get_latest_listen_ts to get the time of the latest listen
    # in spark and so that instead of no stats, outdated stats are calculated.
    latest_listen_date = latest_listen_ts.date()

    # from_offset: this is applied to the latest_listen_date to get from_date
    # to_offset: this is applied to from_date to get to_date

    # "this" time ranges, these count stats for the ongoing time period till date
    if stats_range == "this_week":
        # if today is a monday then from_offset is monday of last week
        # otherwise from_offset is monday of this week
        from_offset = relativedelta(days=-1, weekday=MO(-1))
        to_offset = relativedelta(weeks=+1)
    elif stats_range == "this_month":
        # if today is 1st then 1st of last month otherwise the 1st of this month
        from_offset = relativedelta(months=-1) if latest_listen_date.day == 1 else relativedelta(day=1)
        to_offset = relativedelta(months=+1)
    elif stats_range == "this_year":
        # if today is the 1st of the year, then still show last year stats
        if latest_listen_date.day == 1 and latest_listen_date.month == 1:
            from_offset = relativedelta(years=-1)
        else:
            from_offset = relativedelta(month=1, day=1)
        to_offset = relativedelta(years=+1)

    # following are "last" week/month/year stats, here we want the stats of the
    # previous week/month/year and *not* from 7 days ago to today so on.

    elif stats_range == "week":
        from_offset = relativedelta(weeks=-1, weekday=MO(-1))  # monday of previous week
        to_offset = relativedelta(weeks=+1)
    elif stats_range == "month":
        from_offset = relativedelta(months=-1, day=1)  # first day of previous month
        to_offset = relativedelta(months=+1)
    elif stats_range == "quarter":
        from_offset = get_last_quarter_offset(latest_listen_date)
        to_offset = relativedelta(months=+3)
    elif stats_range == "half_yearly":
        from_offset = get_last_half_year_offset(latest_listen_date)
        to_offset = relativedelta(months=+6)
    else:  # year
        from_offset = relativedelta(years=-1, month=1, day=1)  # first day of previous year
        to_offset = relativedelta(years=+1)

    from_date = latest_listen_date + from_offset
    to_date = from_date + to_offset

    # set time to 00:00
    from_date = datetime.combine(from_date, time.min)
    to_date = datetime.combine(to_date, time.min)

    return from_date, to_date
