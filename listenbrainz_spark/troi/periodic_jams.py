from datetime import datetime, timedelta

from more_itertools import chunked

import listenbrainz_spark
from listenbrainz_spark.path import RECORDING_FEEDBACK_DATAFRAME, RAW_RECOMMENDATIONS
from listenbrainz_spark.stats import run_query

DAYS_OF_RECENT_LISTENS_TO_EXCLUDE = 60
USERS_PER_MESSAGE = 100
MAX_TRACKS_PER_PLAYLIST = 50


def main(slug, users):
    """ Bulk generate troi playlists for the given slug and the given list of users """
    if slug == "weekly-jams":
        max_listened_at = datetime.now() - timedelta(days=DAYS_OF_RECENT_LISTENS_TO_EXCLUDE)
        max_listened_at = max_listened_at.replace(hour=0, minute=0, second=0, microsecond=0)
        time_filter = f"latest_listened_at < to_timestamp('{max_listened_at}')"
    elif slug == "weekly-exploration":
        time_filter = "latest_listened_at IS NULL"
    else:
        return []

    table = "users_periodic_jams"
    users_df = listenbrainz_spark.session.createDataFrame(users)
    users_df.createOrReplaceTempView(table)

    query = f"""
        WITH recommendations AS (
            SELECT user_id
                 , jam_date
                 , recording_mbid
                 , rank() OVER (PARTITION BY user_id ORDER BY score DESC) AS ranking
              FROM {table}
              JOIN parquet.`{RAW_RECOMMENDATIONS}`
             USING (user_id)
         LEFT JOIN parquet.`{RECORDING_FEEDBACK_DATAFRAME}`
             USING (user_id, recording_mbid)
             WHERE {time_filter}
               AND (feedback IS NULL OR feedback != -1)
        ), randomized AS (
            SELECT user_id
                 , jam_date
                 , recording_mbid
                 , rank() over (PARTITION BY user_id ORDER BY RANDOM()) AS position
              FROM recommendations
             WHERE ranking <= {MAX_TRACKS_PER_PLAYLIST}
        )   SELECT user_id
                 , jam_date
                 , array_sort(collect_list(struct(position, recording_mbid))) AS recordings
              FROM randomized
          GROUP BY user_id
                 , jam_date
    """
    data = run_query(query).toLocalIterator()

    for entry in chunked(data, USERS_PER_MESSAGE):
        raw_playlists = [row.asDict(recursive=True) for row in entry]
        playlists = []
        for playlist in raw_playlists:
            playlists.append({
                "user_id": playlist["user_id"],
                "jam_date": playlist["jam_date"],
                "recordings": [r["recording_mbid"] for r in playlist["recordings"]]
            })

        yield {
            "slug": slug,
            "data": playlists,
            "type": "troi_playlists"
        }

    yield {
        "slug": slug,
        "type": "troi_playlists_end"
    }
