from datetime import datetime, date, time

from more_itertools import chunked
from pyspark.sql.types import StructType, StructField, IntegerType

import listenbrainz_spark
from listenbrainz_spark.path import RECORDING_ARTIST_DATAFRAME
from listenbrainz_spark.recommendations.recording.create_dataframes import calculate_dataframes
from listenbrainz_spark.similarity.user import get_similar_users_df
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import get_listens_from_dump
from listenbrainz_spark.year_in_music.utils import create_tracks_of_the_year

USERS_PER_MESSAGE = 1000
MAX_ARTIST_OCCURRENCE = 2
MAX_TRACKS_PER_PLAYLIST = 50
TOP_MISSED_TRACKS_COUNT = 200


def get_similar_users(year):
    # from_date = datetime(year, 1, 1)
    # to_date = datetime.combine(date(year, 12, 31), time.max)
    # calculate_dataframes(from_date, to_date, "similar_users", 50)
    similar_users_df = get_similar_users_df(3)

    users = []
    for row in similar_users_df.toLocalIterator():
        for other_user in row.similar_users:
            users.append((row.user_id, other_user.other_user_id))

    df = listenbrainz_spark.session.createDataFrame(users, schema=StructType([
        StructField("user_id", IntegerType(), nullable=False),
        StructField("other_user_id", IntegerType(), nullable=False)
    ]))
    df.createOrReplaceTempView("similar_users_for_missed_recordings")


def generate_top_missed_recordings(year):
    get_listens_from_dump().createOrReplaceTempView("all_listens")
    create_tracks_of_the_year(year)
    get_similar_users(year)

    query = f"""
        WITH intermediate AS (
            SELECT s.user_id
                 , t.recording_mbid
                 , t.score
              FROM similar_users_for_missed_recordings s
              JOIN tracks_of_year t
                ON s.other_user_id = t.user_id
        ), remove_listened AS (
            SELECT i.user_id
                 , i.recording_mbid
                 , i.score
                 , rank() OVER (PARTITION BY user_id ORDER BY i.score DESC) AS ranking
              FROM intermediate i
             WHERE i.recording_mbid NOT IN (SELECT l.recording_mbid FROM all_listens l WHERE l.user_id = i.user_id)
        ), keep_top_tracks_only AS (
            SELECT user_id
                 , rl.recording_mbid
                 , score
                 , explode(ra.artist_mbids) AS artist_mbid
              FROM remove_listened rl
              JOIN parquet.`{RECORDING_ARTIST_DATAFRAME}` ra
                ON ra.recording_mbid = rl.recording_mbid
            WHERE ranking <= {TOP_MISSED_TRACKS_COUNT}
        ), artist_ranking AS (
            SELECT user_id
                 , recording_mbid
                 , score
                 , rank() OVER (PARTITION BY user_id, artist_mbid ORDER BY score DESC) AS per_artist_position
              FROM keep_top_tracks_only
        ), artist_limiting AS (
            -- need a group by to eliminate duplicate recording mbids in a playlist
            --, can happen when there are multiple artists for a recording
            SELECT user_id
                 , recording_mbid
                 , rank() over (PARTITION BY user_id ORDER BY RANDOM()) AS ranking
              FROM artist_ranking
             WHERE per_artist_position <= {MAX_ARTIST_OCCURRENCE}
          GROUP BY user_id
                 , recording_mbid
        ), playlists AS (
            SELECT user_id
                 , collect_list(recording_mbid) AS recordings
              FROM artist_limiting
             WHERE ranking <= {MAX_TRACKS_PER_PLAYLIST}
          GROUP BY user_id
        )
            SELECT p.user_id
                 , recordings
                 , collect_list(s.other_user_id) AS similar_users
              FROM playlists p
              JOIN similar_users_for_missed_recordings s
                ON p.user_id = s.user_id
          GROUP BY p.user_id
                 , recordings
    """

    data = run_query(query).toLocalIterator()

    for entry in chunked(data, USERS_PER_MESSAGE):
        playlists = [row.asDict(recursive=True) for row in entry]
        yield {
            "slug": "top-missed-recordings",
            "year": year,
            "data": playlists,
            "type": "year_in_music_playlists"
        }

    yield {
        "slug": "top-missed-recordings",
        "year": year,
        "type": "year_in_music_playlists_end"
    }
