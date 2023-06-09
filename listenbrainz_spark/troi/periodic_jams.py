from datetime import datetime, timedelta

from more_itertools import chunked

from listenbrainz_spark.path import RECORDING_FEEDBACK_DATAFRAME, RAW_RECOMMENDATIONS
from listenbrainz_spark.stats import run_query

DAYS_OF_RECENT_LISTENS_TO_EXCLUDE = 60
USERS_PER_MESSAGE = 100


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
                 , rank() OVER (PARTITION BY user_id ORDER BY score DESC) AS position
              FROM parquet.`{RAW_RECOMMENDATIONS}`
         LEFT JOIN parquet.`{RECORDING_FEEDBACK_DATAFRAME}`
             USING (user_id, recording_mbid)
             WHERE {time_filter}
               AND feedback != -1
        )   SELECT user_id
                 , collect_list(struct(position, recording_mbid)) AS recordings
              FROM recommendations
             WHERE position < 50
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
