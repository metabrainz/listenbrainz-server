import json
import logging
from datetime import datetime
from typing import Iterator, Optional, Dict

from pydantic import ValidationError

from data.model.common_stat_spark import StatMessage
from data.model.user_listening_activity import ListeningActivityRecord
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.stats.common.listening_activity import setup_time_range
from listenbrainz_spark.utils import get_listens_from_dump
from pyspark.sql.types import (StringType, StructField, StructType,
                               TimestampType)

time_range_schema = StructType([
    StructField("time_range", StringType()),
    StructField("start", TimestampType()),
    StructField("end", TimestampType())
])


logger = logging.getLogger(__name__)


def calculate_listening_activity(spark_date_format):
    """ Calculate number of listens for each user in time ranges given in the "time_range" table.
    The time ranges are as follows:
        1) week - each day with weekday name of the past 2 weeks.
        2) month - each day the past 2 months.
        3) year - each month of the past 2 years.
        4) all_time - each year starting from LAST_FM_FOUNDING_YEAR (2002)

    Args:
        spark_date_format: the date format
    """
    # calculates the number of listens in each time range for each user, count(listened_at) so that
    # group without listens are counted as 0, count(*) gives 1.
    # this query is much different that the user listening activity stats query because an earlier
    # version of this query which was similar to that caused OutOfMemory on yearly and all time
    # ranges. It turns converting each listened_at to the needed date format and grouping by it is
    # much cheaper than joining with a separate time range table. We still join the grouped data with
    # a separate time range table to fill any gaps i.e. time ranges with no listens get a value of 0
    # instead of being completely omitted from the final result.
    result = run_query(f"""
        WITH bucket_listen_counts AS (
            SELECT date_format(listened_at, '{spark_date_format}') AS time_range
                 , count(listened_at) AS listen_count
              FROM listens
          GROUP BY time_range
        )
            SELECT sort_array(
                       collect_list(
                            struct(
                                  to_unix_timestamp(start) AS from_ts
                                , to_unix_timestamp(end) AS to_ts
                                , time_range
                                , COALESCE(listen_count, 0) AS listen_count
                            )
                        )
                    ) AS listening_activity
              FROM time_range
         LEFT JOIN bucket_listen_counts
             USING (time_range)
    """)
    return result.toLocalIterator()


def get_listening_activity(stats_range: str) -> Iterator[Optional[Dict]]:
    """ Compute the number of listens for a time range compared to the previous range

    Given a time range, this computes a histogram of all listens for that range
    and the previous range of the same duration, so that they can be compared. The
    bin size of the histogram depends on the size of the range (e.g.
    year -> 12 months, month -> ~30 days, week -> ~7 days, see get_time_range for
    details). These values are used on the listening activity reports.
    """
    logger.debug(f"Calculating listening_activity_{stats_range}")
    from_date, to_date, _, _, spark_date_format = setup_time_range(stats_range)
    get_listens_from_dump(from_date, to_date).createOrReplaceTempView("listens")
    data = calculate_listening_activity(spark_date_format)
    messages = create_messages(data=data, stats_range=stats_range, from_date=from_date, to_date=to_date)
    logger.debug("Done!")
    return messages


def create_messages(data, stats_range: str, from_date: datetime, to_date: datetime) \
        -> Iterator[Optional[Dict]]:
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
    message = {
        "type": "sitewide_listening_activity",
        "stats_range": stats_range,
        "from_ts": int(from_date.timestamp()),
        "to_ts": int(to_date.timestamp())
    }

    _dict = next(data).asDict(recursive=True)
    message["data"] = _dict["listening_activity"]
    try:
        model = StatMessage[ListeningActivityRecord](**message)
        result = model.dict(exclude_none=True)
        yield result
    except ValidationError:
        logger.error(f"""ValidationError while calculating {stats_range} listening_activity for user: 
        Data: {json.dumps(_dict, indent=3)}""", exc_info=True)
        yield None
