from calendar import monthrange
from datetime import datetime
from dateutil.relativedelta import relativedelta

import listenbrainz_spark
from listenbrainz_spark.exceptions import SQLException

from pyspark.sql.utils import *


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
        processed_query = listenbrainz_spark.sql_context.sql(query)
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
    return datetime(day.year, day.month, day.day, hour=23, minute=59, second=59)


def get_month_end(month: datetime) -> datetime:
    """ Returns a datetime object denoting the end of the month """
    _, num_of_days = monthrange(month.year, month.month)
    return datetime(month.year, month.month, num_of_days, hour=23, minute=59, second=59)


def get_year_end(year: int) -> datetime:
    """ Returns a datetime object denoting the end of the year """
    return datetime(year, month=12, day=31, hour=23, minute=59, second=59)
