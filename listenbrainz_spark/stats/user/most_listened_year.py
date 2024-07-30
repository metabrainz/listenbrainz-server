from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import Iterator, Optional, Dict
import logging
import json

from more_itertools import chunked
from pydantic import ValidationError

from listenbrainz_spark.path import RELEASE_METADATA_CACHE_DATAFRAME
from listenbrainz_spark.postgres import create_release_metadata_cache
from listenbrainz_spark.utils import read_files_from_HDFS
from listenbrainz_spark.year_in_music.utils import get_listens_from_dump
from listenbrainz_spark.stats import run_query
from data.model.common_stat_spark import UserStatRecords

USERS_PER_MESSAGE = 25

logger = logging.getLogger(__name__)

def get_most_listened_year(year: int, month: Optional[int], day: Optional[int], database: str = None):
    logger.debug(f"Calculating most_listened_year_for_{year}_{month}_{day}")

    if year and month is None and day is None:
        from_date = datetime(year, 1, 1)
        to_date = from_date + relativedelta(years=1)
        stats_range = "year"
    elif year and month and day is None:
        from_date = datetime(year, month, 1)
        to_date = from_date + relativedelta(months=1)
        stats_range = "month"
    elif year and month and day:
        from_date = datetime(year, month, day)
        to_date = from_date + relativedelta(days=1)
        stats_range = "date"
    else:
        raise ValueError("Invalid input: Provide at least a year, and optionally month and date.")

    get_listens_from_dump(from_date, to_date).createOrReplaceTempView("listens")

    create_release_metadata_cache()
    read_files_from_HDFS(RELEASE_METADATA_CACHE_DATAFRAME).createOrReplaceTempView(
        "releases_all"
    )

    data = run_query(_get_releases_with_date()).toLocalIterator()

    messages = create_messages(data, stats_range, from_date, to_date, database)
    logger.debug("Done!")

    return messages


def _get_releases_with_date():
    return """
          WITH listen_year AS (
        SELECT user_id
             , rel.first_release_date_year AS year
             , count(*) AS listen_count
          FROM listens l
          JOIN releases_all rel
            ON l.release_mbid = rel.release_mbid
         WHERE first_release_date_year IS NOT NULL
      GROUP BY user_id
             , rel.first_release_date_year
        )
        SELECT user_id
             , map_from_entries(
                     collect_list(
                         struct(year, listen_count)
                     )
               ) AS most_listened_year
          FROM listen_year
      GROUP BY user_id
    """


def create_messages(data, stats_range: str, from_date: datetime, to_date: datetime, database: Optional[str] = None) \
        -> Iterator[Optional[Dict]]:

    if database is None:
        database = f'most_listened_year_{stats_range}'

    yield {"type": "couchdb_data_start", "database": database}

    from_ts = int(from_date.timestamp())
    to_ts = int(to_date.timestamp())

    for entries in chunked(data, USERS_PER_MESSAGE):
        multiple_user_stats = []
        for entry in entries:
            _dict = entry.asDict(recursive=True)
            try:
                logger.debug(f"Inserting most_listened_year for user: {_dict['user_id']}")
                logger.debug(f"Data: {json.dumps(_dict, indent=3)}")
                UserStatRecords(user_id=_dict["user_id"], data=_dict["most_listened_year"])
                multiple_user_stats.append(
                    {"user_id": _dict["user_id"], "data": _dict["most_listened_year"]}
                )
            except ValidationError:
                logger.error(
                    f"""ValidationError while calculating {stats_range} most_listened_year for user:
                {_dict["user_id"]}. Data: {json.dumps(_dict, indent=3)}""",
                    exc_info=True,
                )
        
        logger.debug(f"Inserting {len(multiple_user_stats)} user stats")

        yield {
            "type": "user_most_listened_year",
            "stats_range": stats_range,
            "from_ts": from_ts,
            "to_ts": to_ts,
            "data": multiple_user_stats,
            "database": database,
        }

    yield {"type": "couchdb_data_end", "database": database}
