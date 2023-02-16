import json
import logging
from datetime import datetime
from typing import Iterator, Optional, Dict

from more_itertools import chunked
from pydantic import ValidationError

from data.model.common_stat_spark import UserStatRecords, StatMessage
from data.model.user_listening_activity import ListeningActivityRecord
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.stats.common.listening_activity import setup_time_range
from listenbrainz_spark.stats.user import USERS_PER_MESSAGE
from listenbrainz_spark.utils import get_listens_from_dump


logger = logging.getLogger(__name__)


def calculate_listening_activity():
    """ Calculate number of listens for each user in time ranges given in the "time_range" table.
    The time ranges are as follows:
        1) week - each day with weekday name of the past 2 weeks
        2) month - each day the past 2 months
        3) quarter - each week of past 2 quarters
        4) half_yearly - each month of past 2 half-years
        5) year - each month of the past 2 years
        4) all_time - each year starting from LAST_FM_FOUNDING_YEAR (2002)
    """
    # calculates the number of listens in each time range for each user, count(listen.listened_at) so that
    # group without listens are counted as 0, count(*) gives 1.
    result = run_query(""" 
        WITH dist_user_id AS (
            SELECT DISTINCT user_id FROM listens
        ), intermediate_table AS (
            SELECT dist_user_id.user_id AS user_id
                 , to_unix_timestamp(first(time_range.start)) as from_ts
                 , to_unix_timestamp(first(time_range.end)) as to_ts
                 , time_range.time_range AS time_range
                 , count(listens.listened_at) as listen_count
              FROM dist_user_id
        CROSS JOIN time_range
         LEFT JOIN listens
                ON listens.listened_at BETWEEN time_range.start AND time_range.end
               AND listens.user_id = dist_user_id.user_id
          GROUP BY dist_user_id.user_id
                 , time_range.time_range
        )
            SELECT user_id
                 , sort_array(
                       collect_list(
                           struct(from_ts, to_ts, time_range, listen_count)
                        )
                    ) AS listening_activity
              FROM intermediate_table
          GROUP BY user_id
    """)
    return result.toLocalIterator()


def get_listening_activity(stats_range: str, message_type="user_listening_activity", database: str = None)\
        -> Iterator[Optional[Dict]]:
    """ Compute the number of listens for a time range compared to the previous range

    Given a time range, this computes a histogram of a users' listens for that range
    and the previous range of the same duration, so that they can be compared. The
    bin size of the histogram depends on the size of the range (e.g.
    year -> 12 months, month -> ~30 days, week -> ~7 days, see get_time_range for
    details). These values are used on the listening activity reports.
    """
    logger.debug(f"Calculating listening_activity_{stats_range}")
    from_date, to_date, _, _, _ = setup_time_range(stats_range)
    get_listens_from_dump(from_date, to_date).createOrReplaceTempView("listens")
    data = calculate_listening_activity()
    messages = create_messages(data=data, stats_range=stats_range,
                               from_date=from_date, to_date=to_date,
                               message_type=message_type, database=database)
    logger.debug("Done!")
    return messages


def create_messages(data, stats_range: str, from_date: datetime, to_date: datetime,
                    message_type: str, database: str = None) -> Iterator[Optional[Dict]]:
    """
    Create messages to send the data to webserver via RabbitMQ

    Args:
        data: Data to send to webserver
        stats_range: The range for which the statistics have been calculated
        from_date: The start time of the stats
        to_date: The end time of the stats
        message_type: used to decide which handler on LB webserver side should
            handle this message. can be "user_entity" or "year_in_music_listens_per_day"
        database: the name of the database in which the webserver should store the data
    Returns:
        messages: A list of messages to be sent via RabbitMQ
    """
    if database is None:
        database = f"listening_activity_{stats_range}"

    yield {
        "type": "couchdb_data_start",
        "database": database
    }

    from_ts = int(from_date.timestamp())
    to_ts = int(to_date.timestamp())

    for entries in chunked(data, USERS_PER_MESSAGE):
        multiple_user_stats = []
        for entry in entries:
            _dict = entry.asDict(recursive=True)
            try:
                user_stat = UserStatRecords[ListeningActivityRecord](
                    user_id=_dict["user_id"],
                    data=_dict["listening_activity"]
                )
                multiple_user_stats.append(user_stat)
            except ValidationError:
                logger.error(f"""ValidationError while calculating {stats_range} listening_activity for user:
                {_dict["user_id"]}. Data: {json.dumps(_dict, indent=3)}""", exc_info=True)

        try:
            model = StatMessage[UserStatRecords[ListeningActivityRecord]](**{
                "type": message_type,
                "stats_range": stats_range,
                "from_ts": from_ts,
                "to_ts": to_ts,
                "data": multiple_user_stats,
                "database": database
            })
            result = model.dict(exclude_none=True)
            yield result
        except ValidationError:
            logger.error(f"ValidationError while calculating {stats_range} listening_activity:", exc_info=True)
            yield None

    yield {
        "type": "couchdb_data_end",
        "database": database
    }
