import logging

from more_itertools import chunked

from listenbrainz_spark.stats import run_query, get_dates_for_stats_range
from listenbrainz_spark.utils import get_listens_from_new_dump

logger = logging.getLogger(__name__)
USERS_PER_MESSAGE = 5
TRACKS_PER_USER = 200


def calculate_top_tracks_bubble_chart(table: str, limit: int):
    return run_query(
        f"""
            WITH intermediate_1 AS (
                SELECT user_name
                     , artist_name
                     , recording_name
                     , release_name
                     , count(*) as listen_count
                  FROM {table}
                 WHERE recording_mbid IS NOT NULL 
              GROUP BY user_name
                     , recording_name
                     , release_name
                     , artist_name
            ), intermediate_2 AS (
                SELECT user_name
                     , artist_name
                     , recording_name
                     , release_name
                     , listen_count
                     , row_number() OVER(PARTITION BY user_name ORDER BY listen_count) AS row
                  FROM intermediate_1
            ), intermediate_3 AS (
                SELECT user_name
                     , artist_name
                     , struct(
                          release_name AS name
                        , collect_list(
                             struct(
                                listen_count
                              , recording_name AS name
                             )
                          ) AS children
                       ) AS data
                  FROM intermediate_2
                 WHERE row <= {limit}  
              GROUP BY user_name
                     , artist_name
                     , release_name
            ), intermediate_4 AS (
                SELECT user_name
                     , struct(
                          artist_name AS name
                        , collect_list(data) AS children
                       ) AS data
                  FROM intermediate_3
              GROUP BY user_name
                     , artist_name
            )
            SELECT user_name
                 , to_json(
                     collect_list(data)
                 ) AS stats
              FROM intermediate_4
          GROUP BY user_name
        """
    ).toLocalIterator()


def get_top_tracks_bubble_chart(stats_range: str):
    """ Get top tracks of users for bubble charts """
    logger.debug(f"Calculating top_tracks_bubble_chart_{stats_range}...")

    from_date, to_date = get_dates_for_stats_range(stats_range)
    listens_df = get_listens_from_new_dump(from_date, to_date)
    table = f"user_top_tracks_bubble_{stats_range}"
    listens_df.createOrReplaceTempView(table)

    data = calculate_top_tracks_bubble_chart(table, TRACKS_PER_USER)
    from_ts = int(from_date.timestamp())
    to_ts = int(to_date.timestamp())

    for entries in chunked(data, USERS_PER_MESSAGE):
        yield {
            "type": "user_top_tracks_bubble",
            "stats_range": stats_range,
            "from_ts": from_ts,
            "to_ts": to_ts,
            "data": list(entries),
        }

    logger.debug("Done!")
