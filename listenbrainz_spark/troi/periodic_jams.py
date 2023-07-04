from datetime import datetime, timedelta

from more_itertools import chunked

from listenbrainz_spark.path import RECORDING_FEEDBACK_DATAFRAME, RAW_RECOMMENDATIONS
from listenbrainz_spark.stats import run_query

DAYS_OF_RECENT_LISTENS_TO_EXCLUDE = 60
USERS_PER_MESSAGE = 100
MAX_TRACKS_PER_PLAYLIST = 50


def main(slug):
    """ Bulk generate troi playlists for the given slug """
    if slug == "weekly-jams":
        max_listened_at = datetime.now() - timedelta(days=DAYS_OF_RECENT_LISTENS_TO_EXCLUDE)
        max_listened_at = max_listened_at.replace(hour=0, minute=0, second=0, microsecond=0)
        time_filter = f"latest_listened_at < to_timestamp('{max_listened_at}')"
    elif slug == "weekly-exploration":
        time_filter = "latest_listened_at IS NULL"
    else:
        return []

    query = f"""
        WITH recommendations AS (
            SELECT user_id
                 , recording_mbid
                 , rank() OVER (PARTITION BY user_id ORDER BY score DESC) AS ranking
              FROM parquet.`{RAW_RECOMMENDATIONS}`
         LEFT JOIN parquet.`{RECORDING_FEEDBACK_DATAFRAME}`
             USING (user_id, recording_mbid)
             WHERE {time_filter}
               AND (feedback IS NULL OR feedback != -1)
        ), randomized AS (
            SELECT user_id
                 , recording_mbid
                 , rank() over (PARTITION BY user_id ORDER BY RANDOM()) AS position
              FROM recommendations
             WHERE ranking <= {MAX_TRACKS_PER_PLAYLIST}
        )   SELECT user_id
                 , collect_list(recording_mbid) OVER (PARTITION BY user_id ORDER BY position) AS recordings
              FROM randomized
          GROUP BY user_id
    """
    data = run_query(query).toLocalIterator()

    for entry in chunked(data, USERS_PER_MESSAGE):
        playlists = [row.asDict(recursive=True) for row in entry]
        yield {
            "slug": slug,
            "data": playlists,
            "type": "troi_playlists"
        }

    yield {
        "slug": slug,
        "type": "troi_playlists_end"
    }
