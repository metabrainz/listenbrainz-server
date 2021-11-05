import json
import logging
from datetime import datetime, time, date
from typing import Iterator, Optional, Tuple

from dateutil.relativedelta import relativedelta, MO
from pydantic import ValidationError

import listenbrainz_spark
from data.model.user_listening_activity import UserListeningActivityStatMessage
from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import get_listens_from_new_dump, get_latest_listen_ts
from pyspark.sql.functions import collect_list, sort_array, struct
from pyspark.sql.types import (StringType, StructField, StructType,
                               TimestampType)

time_range_schema = StructType([
    StructField("time_range", StringType()),
    StructField("start", TimestampType()),
    StructField("end", TimestampType())
])


logger = logging.getLogger(__name__)


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


# other stats uses a different function (get_dates_for_stats_range) to calculate
# time ranges. if making modifications here, remember to check and update that as well
def get_time_range(stats_range: str) -> Tuple[datetime, datetime, relativedelta, str]:
    latest_listen_ts = get_latest_listen_ts()
    if stats_range == "all_time":
        # all_time stats range is easy, just return time from LASTFM founding
        # to the latest listen we have in spark
        from_date = datetime(LAST_FM_FOUNDING_YEAR, 1, 1)
        to_date = latest_listen_ts
        # compute listening activity on annual basis
        step = relativedelta(years=+1)
        date_format = "%Y"
        return from_date, to_date, step, date_format

    # following are "last" week/month/year stats, here we want the stats of the
    # previous week/month/year and *not* from 7 days ago to today so on.

    # If we had used datetime.now or date.today here and the data in spark
    # became outdated due to some reason, empty stats would be sent to LB.
    # Hence, we use get_latest_listen_ts to get the time of the latest listen
    # in spark and so that instead of no stats, outdated stats are calculated.
    latest_listen_date = latest_listen_ts.date()

    # from_offset: this is applied to the latest_listen_date to get from_date
    # to_offset: this is applied to from_date to get to_date
    if stats_range == "week":
        from_offset = relativedelta(weeks=-2, weekday=MO(-1))
        to_offset = relativedelta(weeks=+2)
        # compute listening activity for each day, include weekday in date format
        step = relativedelta(days=+1)
        date_format = "%A %d %B %Y"
    elif stats_range == "month":
        from_offset = relativedelta(months=-2, day=1)  # start of the previous to previous month
        to_offset = relativedelta(months=+2)
        # compute listening activity for each day but no weekday
        step = relativedelta(days=+1)
        date_format = "%d %B %Y"
    elif stats_range == "quarter":
        from_offset = get_two_quarters_ago_offset(latest_listen_date)
        to_offset = relativedelta(months=+6)
        # compute listening activity for each week with date format as day
        step = relativedelta(weeks=+1)
        date_format = "%d %B %Y"
    else:  # year
        from_offset = relativedelta(years=-2, month=1, day=1)  # start of the previous to previous year
        to_offset = relativedelta(years=+2)
        step = relativedelta(months=+1)
        # compute listening activity for each month
        date_format = "%B %Y"

    from_date = latest_listen_date + from_offset
    to_date = from_date + to_offset

    # set time to 00:00
    from_date = datetime.combine(from_date, time.min)
    to_date = datetime.combine(to_date, time.min)

    return from_date, to_date, step, date_format


def calculate_listening_activity():
    """ Calculate number of listens for each user in time ranges given in the "time_range" table.
    The time ranges are as follows:
        1) week - each day with weekday name of the past 2 weeks.
        2) month - each day the past 2 months. 
        3) year - each month of the past 2 years.
        4) all_time - each year starting from LAST_FM_FOUNDING_YEAR (2002)
    """
    # calculates the number of listens in each time range for each user, count(listen.listened_at) so that
    # group without listens are counted as 0, count(*) gives 1.
    result = run_query(""" 
    WITH dist_user_name AS (
            SELECT DISTINCT user_name FROM listens
        ),
        intermediate_table AS (
            SELECT dist_user_name.user_name AS user_name
                 , to_unix_timestamp(first(time_range.start)) as from_ts
                 , to_unix_timestamp(first(time_range.end)) as to_ts
                 , time_range.time_range AS time_range
                 , count(listens.listened_at) as listen_count
              FROM dist_user_name
        CROSS JOIN time_range
         LEFT JOIN listens
                ON listens.listened_at BETWEEN time_range.start AND time_range.end
               AND listens.user_name = dist_user_name.user_name
          GROUP BY dist_user_name.user_name
                 , time_range.time_range
        )
            SELECT user_name
                 , sort_array(
                       collect_list(
                           struct(from_ts, to_ts, time_range, listen_count)
                        )
                    ) AS listening_activity
              FROM intermediate_table
          GROUP BY user_name
    """)
    return result.toLocalIterator()


def get_listening_activity(stats_range: str):
    """ Compute the number of listens for a time range compared to the previous range

    Given a time range, this computes a histogram of a users' listens for that range
    and the previous range of the same duration, so that they can be compared. The
    bin size of the histogram depends on the size of the range (e.g.
    year -> 12 months, month -> ~30 days, week -> ~7 days, see get_time_range for
    details). These values are used on the listening activity reports.
    """
    logger.debug(f"Calculating listening_activity_{stats_range}")

    from_date, to_date, step, date_format = get_time_range(stats_range)
    time_range = []

    period_start = from_date
    while period_start < to_date:
        period_formatted = period_start.strftime(date_format)
        # calculate the time at which this period ends i.e. 1 microsecond before the next period's start
        # here, period_start + step is next period's start
        period_end = period_start + step + relativedelta(microseconds=-1)
        time_range.append([period_formatted, period_start, period_end])
        period_start = period_start + step

    time_range_df = listenbrainz_spark.session.createDataFrame(time_range, time_range_schema)
    time_range_df.createOrReplaceTempView("time_range")

    get_listens_from_new_dump(from_date, to_date).createOrReplaceTempView("listens")
    data = calculate_listening_activity()
    messages = create_messages(data=data, stats_range=stats_range, from_date=from_date, to_date=to_date)

    logger.debug("Done!")

    return messages


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
