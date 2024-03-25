from datetime import datetime, timedelta

from more_itertools import chunked

import listenbrainz_spark
from listenbrainz_spark.path import RECORDING_FEEDBACK_DATAFRAME, RAW_RECOMMENDATIONS, RECORDING_ARTIST_DATAFRAME
from listenbrainz_spark.stats import run_query

DAYS_OF_RECENT_LISTENS_TO_EXCLUDE = 60
USERS_PER_MESSAGE = 100
MAX_TRACKS_PER_PLAYLIST = 50
MAX_ARTIST_OCCURRENCE = 2


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

    if not users:
        return []

    table = "users_periodic_jams"
    users_df = listenbrainz_spark.session.createDataFrame(users)
    users_df.createOrReplaceTempView(table)

    query = f"""
        WITH recommendations AS (
            SELECT user_id
                 , jam_date
                 , rr.recording_mbid
                 , score
                 , explode(ra.artist_mbids) AS artist_mbid
              FROM {table}
              JOIN parquet.`{RAW_RECOMMENDATIONS}` rr
             USING (user_id)
         LEFT JOIN parquet.`{RECORDING_FEEDBACK_DATAFRAME}` rf
             USING (user_id, recording_mbid)
              JOIN parquet.`{RECORDING_ARTIST_DATAFRAME}` ra
                ON rr.recording_mbid = ra.recording_mbid
             WHERE {time_filter}
               AND (feedback IS NULL OR feedback != -1)
        ), artist_ranking AS (
            SELECT user_id
                 , jam_date
                 , recording_mbid
                 , score
                 , rank() OVER (PARTITION BY user_id, artist_mbid ORDER BY score DESC) AS per_artist_position
              FROM recommendations
        ), artist_limiting AS (
            -- need a group by to eliminate duplicate recording mbids in a playlist
            --, can happen when there are multiple artists for a recording
            SELECT user_id
                 , jam_date
                 , recording_mbid
                 , rank() over (PARTITION BY user_id ORDER BY RANDOM()) AS ranking
              FROM artist_ranking
             WHERE per_artist_position <= {MAX_ARTIST_OCCURRENCE}
          GROUP BY user_id
                 , jam_date
                 , recording_mbid
        )
            SELECT user_id
                 , jam_date
                 , collect_list(recording_mbid) AS recordings
              FROM artist_limiting
             WHERE ranking <= {MAX_TRACKS_PER_PLAYLIST}
          GROUP BY user_id
                 , jam_date
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
